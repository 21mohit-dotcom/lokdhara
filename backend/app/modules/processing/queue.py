"""PostgreSQL job queue (ADR-019): enqueue inside the caller's transaction, claim with
FOR UPDATE SKIP LOCKED, retry with backoff, recover jobs from crashed workers.

Logs and stored errors carry codes and job IDs only, never payload content.
"""

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Engine, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.processing.models import JOB_TYPES, Job, ProcessingRun

logger = logging.getLogger("lokdhara.jobs")

MAX_BACKOFF = timedelta(hours=1)


@dataclass(frozen=True)
class JobContext:
    """What a handler receives. `db` is committed together with the job's success.

    `run_id` is the ID this attempt's `processing_runs` row will get, so rows the handler
    writes (renditions) can point to the run that made them.
    """

    job_id: uuid.UUID
    job_type: str
    payload: dict[str, Any]
    target_type: str | None
    target_id: uuid.UUID | None
    attempt: int
    db: Session
    run_id: uuid.UUID


@dataclass(frozen=True)
class JobResult:
    output_summary: dict[str, Any] = field(default_factory=dict)
    tool_versions: dict[str, Any] = field(default_factory=dict)
    input_sha256: str | None = None


class JobError(Exception):
    """An expected failure. `detail` is stored, so it must not contain content or names."""

    def __init__(self, code: str, detail: str | None = None, *, retryable: bool = True) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.retryable = retryable


Handler = Callable[[JobContext], JobResult]
_handlers: dict[str, Handler] = {}

# Called with (db, job) in the transaction that settles a job: it succeeded, failed for good, or
# an admin queued it again. The job row already shows its new status.
Listener = Callable[[Session, Job], None]
_listeners: list[Listener] = []


def handler(job_type: str) -> Callable[[Handler], Handler]:
    """Registers the function that runs jobs of `job_type`."""
    if job_type not in JOB_TYPES:
        raise ValueError(f"unknown job type {job_type!r}")

    def register(func: Handler) -> Handler:
        _handlers[job_type] = func
        return func

    return register


def on_job_changed(func: Listener) -> Listener:
    """Registers a function that follows job outcomes, such as a submission's status."""
    _listeners.append(func)
    return func


def notify_changed(db: Session, job_id: uuid.UUID) -> None:
    job = db.get(Job, job_id, populate_existing=True)
    if job is None:
        return
    for listener in _listeners:
        listener(db, job)


def utcnow() -> datetime:
    return datetime.now(UTC)


def backoff(attempt: int) -> timedelta:
    """30 s, 1 min, 2 min, … capped at one hour."""
    return min(timedelta(seconds=30 * 2 ** max(attempt - 1, 0)), MAX_BACKOFF)


def enqueue(
    db: Session,
    job_type: str,
    *,
    payload: dict[str, Any] | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    dedupe_key: str | None = None,
    delay: timedelta | None = None,
    max_attempts: int = 5,
) -> uuid.UUID | None:
    """Adds a job to the caller's transaction; it becomes visible when the caller commits.

    Returns None when a pending job with the same dedupe_key already exists.
    """
    if job_type not in JOB_TYPES:
        raise ValueError(f"unknown job type {job_type!r}")
    stmt = (
        insert(Job)
        .values(
            job_type=job_type,
            payload=payload or {},
            target_type=target_type,
            target_id=target_id,
            dedupe_key=dedupe_key,
            max_attempts=max_attempts,
            run_after=utcnow() + (delay or timedelta(0)),
        )
        .on_conflict_do_nothing(
            index_elements=[Job.dedupe_key],
            index_where=text("dedupe_key IS NOT NULL AND status IN ('queued', 'running')"),
        )
        .returning(Job.id)
    )
    return db.execute(stmt).scalar_one_or_none()


@dataclass(frozen=True)
class ClaimedJob:
    id: uuid.UUID
    job_type: str
    payload: dict[str, Any]
    target_type: str | None
    target_id: uuid.UUID | None
    attempt: int
    max_attempts: int
    run_id: uuid.UUID


_CLAIM = text(
    """
    UPDATE jobs
       SET status = 'running',
           attempts = attempts + 1,
           locked_by = :worker_id,
           lock_expires_at = now() + make_interval(secs => :lease_seconds)
     WHERE id = (
           SELECT id FROM jobs
            WHERE (status = 'queued' AND run_after <= now())
               OR (status = 'running' AND lock_expires_at < now())
            ORDER BY run_after, id
            LIMIT 1
              FOR UPDATE SKIP LOCKED)
    RETURNING id, job_type, payload, target_type, target_id, attempts, max_attempts,
              uuidv7() AS run_id
    """
)


def claim(engine: Engine, worker_id: str, lease_seconds: float) -> ClaimedJob | None:
    """Takes the next due job, or one whose worker died (expired lease)."""
    with engine.begin() as connection:
        row = connection.execute(
            _CLAIM, {"worker_id": worker_id, "lease_seconds": lease_seconds}
        ).first()
    if row is None:
        return None
    return ClaimedJob(
        id=row.id,
        job_type=row.job_type,
        payload=row.payload,
        target_type=row.target_type,
        target_id=row.target_id,
        attempt=row.attempts,
        max_attempts=row.max_attempts,
        run_id=row.run_id,
    )


def _release(job: ClaimedJob, worker_id: str, **values: Any) -> Any:
    """UPDATE for a job this worker still holds; a lost lease means another worker owns it."""
    return (
        update(Job)
        .where(Job.id == job.id, Job.locked_by == worker_id, Job.status == "running")
        .values(locked_by=None, lock_expires_at=None, **values)
    )


def _record_run(
    db: Session,
    job: ClaimedJob,
    worker_id: str,
    started_at: datetime,
    status: str,
    result: JobResult | None = None,
    error_code: str | None = None,
    error_detail: str | None = None,
) -> None:
    db.add(
        ProcessingRun(
            id=job.run_id,
            job_id=job.id,
            job_type=job.job_type,
            target_type=job.target_type,
            target_id=job.target_id,
            attempt=job.attempt,
            status=status,
            started_at=started_at,
            finished_at=utcnow(),
            worker_id=worker_id,
            tool_versions=result.tool_versions if result else {},
            input_sha256=result.input_sha256 if result else None,
            output_summary=result.output_summary if result else {},
            error_code=error_code,
            error_detail=error_detail,
        )
    )


def _fail(
    engine: Engine, job: ClaimedJob, worker_id: str, started_at: datetime, error: JobError
) -> None:
    retry = error.retryable and job.attempt < job.max_attempts
    with Session(engine) as db:
        _record_run(db, job, worker_id, started_at, "failed", None, error.code, error.detail)
        if retry:
            values: dict[str, Any] = {
                "status": "queued",
                "run_after": utcnow() + backoff(job.attempt),
                "last_error_code": error.code,
            }
        else:
            values = {"status": "failed", "finished_at": utcnow(), "last_error_code": error.code}
        released = db.execute(_release(job, worker_id, **values))
        if not retry and released.rowcount == 1:  # type: ignore[attr-defined]
            notify_changed(db, job.id)
        db.commit()
    logger.warning(
        "job failed",
        extra={
            "job_id": str(job.id),
            "job_type": job.job_type,
            "attempt": job.attempt,
            "error_code": error.code,
            "will_retry": retry,
        },
    )


def process_one(engine: Engine, worker_id: str, lease_seconds: float) -> bool:
    """Runs at most one job. Returns False when nothing was due."""
    job = claim(engine, worker_id, lease_seconds)
    if job is None:
        return False
    started_at = utcnow()
    if job.attempt > job.max_attempts:  # recovered from a worker that kept crashing
        _fail(engine, job, worker_id, started_at, JobError("attempts_exhausted", retryable=False))
        return True
    run = _handlers.get(job.job_type)
    if run is None:
        _fail(engine, job, worker_id, started_at, JobError("no_handler", retryable=False))
        return True
    with Session(engine, expire_on_commit=False) as db:
        context = JobContext(
            job.id,
            job.job_type,
            job.payload,
            job.target_type,
            job.target_id,
            job.attempt,
            db,
            job.run_id,
        )
        try:
            result = run(context)
        except JobError as error:
            db.rollback()
            _fail(engine, job, worker_id, started_at, error)
            return True
        except Exception as error:
            db.rollback()
            # Exception messages may quote data; store only the exception's type.
            unexpected = JobError("unexpected_error", type(error).__name__)
            _fail(engine, job, worker_id, started_at, unexpected)
            return True
        _record_run(db, job, worker_id, started_at, "succeeded", result)
        released = db.execute(
            _release(job, worker_id, status="succeeded", finished_at=utcnow(), last_error_code=None)
        )
        if released.rowcount != 1:  # type: ignore[attr-defined]
            # The lease expired and another worker took the job: discard this attempt's writes.
            db.rollback()
            logger.warning("job lease lost", extra={"job_id": str(job.id)})
            return True
        try:
            notify_changed(db, job.id)
        except Exception as error:
            db.rollback()
            unexpected = JobError("unexpected_error", type(error).__name__)
            _fail(engine, job, worker_id, started_at, unexpected)
            return True
        db.commit()
    logger.info(
        "job succeeded",
        extra={"job_id": str(job.id), "job_type": job.job_type, "attempt": job.attempt},
    )
    return True
