"""Admin operations on jobs (docs/API_SPECIFICATION.md §9)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.modules.audit import service as audit
from app.modules.audit.service import RequestContext
from app.modules.identity.service import AuthenticatedUser
from app.modules.processing.models import Job
from app.modules.processing.queue import utcnow


def list_jobs(db: Session, status: str, limit: int) -> list[Job]:
    return list(
        db.scalars(
            select(Job)
            .where(Job.status == status)
            .order_by(Job.finished_at.desc().nulls_last(), Job.created_at.desc())
            .limit(limit)
        )
    )


def retry_job(
    db: Session, *, actor: AuthenticatedUser, job_id: uuid.UUID, context: RequestContext
) -> Job:
    job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if job is None:
        raise ApiError(404, "job_not_found", "Job not found.")
    if job.status != "failed":
        raise ApiError(409, "job_not_failed", "Only failed jobs can be retried.")
    job.status = "queued"
    job.attempts = 0
    job.run_after = utcnow()
    job.finished_at = None
    audit.record(
        db,
        action="job.retry",
        context=context,
        actor_user_id=actor.id,
        target_type="job",
        target_id=job.id,
        details={"job_type": job.job_type, "last_error_code": job.last_error_code},
    )
    db.commit()
    return job
