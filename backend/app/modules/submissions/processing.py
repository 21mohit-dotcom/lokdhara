"""Worker jobs for recordings (docs/AUDIO_PROCESSING_PIPELINE.md §3, docs/DATA_LIFECYCLE.md).

`audio.validate` downloads the quarantined upload to a private temporary folder, probes and
fully decodes it, and then either promotes it to originals (a verified byte-for-byte copy under
the same key, ADR-009) or rejects it with a code. `cleanup.quarantine` then removes the
quarantine copy. No database transaction stays open while files are copied or decoded.
"""

import hashlib
import tempfile
import uuid
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio import ffmpeg
from app.audio.validation import AudioInfo, Limits, Rejection, check_decode, check_probe
from app.config import Settings, get_settings
from app.modules.processing import queue
from app.modules.processing.queue import JobContext, JobError, JobResult, handler, utcnow
from app.modules.submissions.models import Recording, Submission
from app.object_store import (
    Bucket,
    IntegrityError,
    ObjectExists,
    ObjectNotFound,
    ObjectStore,
    get_object_store,
)


def limits(settings: Settings) -> Limits:
    return Limits(
        max_seconds=settings.max_audio_seconds,
        max_channels=settings.max_audio_channels,
        min_sample_rate_hz=settings.min_sample_rate_hz,
        max_sample_rate_hz=settings.max_sample_rate_hz,
    )


def _recording(db: Session, recording_id: uuid.UUID | None, *, lock: bool = False) -> Recording:
    query = select(Recording).where(Recording.id == recording_id)
    recording = db.scalar(query.with_for_update() if lock else query)
    if recording is None:
        raise JobError("recording_not_found", retryable=False)
    return recording


def _download(store: ObjectStore, key: str, sha256: str, path: Path) -> None:
    """Copies the quarantined upload to `path`, proving it is the file that was uploaded."""
    digest = hashlib.sha256()
    try:
        with path.open("wb") as file:
            for chunk in store.open(Bucket.QUARANTINE, key):
                digest.update(chunk)
                file.write(chunk)
    except ObjectNotFound as exc:
        raise JobError("quarantine_missing", retryable=False) from exc
    if digest.hexdigest() != sha256:
        raise JobError("checksum_mismatch", retryable=False)


def _inspect(
    path: Path, container: str, settings: Settings
) -> tuple[ffmpeg.Probe | None, AudioInfo | Rejection, int | None]:
    timeout = settings.ffmpeg_timeout_seconds
    try:
        found = ffmpeg.probe(path, container, timeout=timeout)
        verdict = check_probe(found, limits(settings))
        if isinstance(verdict, Rejection):
            return found, verdict, None
        decoded = ffmpeg.decode(
            path, container, timeout=timeout, max_seconds=settings.max_audio_seconds
        )
    except ffmpeg.FfmpegTimeout as exc:
        # Deterministic for this file, so retrying would only repeat it; an admin can retry.
        raise JobError("ffmpeg_timeout", retryable=False) from exc
    return found, check_decode(decoded, limits(settings)) or verdict, decoded.duration_ms


def _promote(store: ObjectStore, key: str, sha256: str) -> None:
    try:
        store.copy_verified(Bucket.QUARANTINE, key, Bucket.ORIGINALS, key, sha256)
    except ObjectExists:
        # An earlier attempt copied it but did not finish; originals are never overwritten.
        if store.sha256_of(Bucket.ORIGINALS, key) != sha256:
            raise JobError("original_mismatch", retryable=False) from None
    except IntegrityError as exc:
        raise JobError("copy_mismatch") from exc


@handler("audio.validate")
def validate_recording(context: JobContext) -> JobResult:
    settings, store, db = get_settings(), get_object_store(), context.db
    recording = _recording(db, context.target_id)
    if recording.upload_status != "quarantined":  # already decided: re-running changes nothing
        return JobResult(output_summary={"skipped": recording.upload_status})
    key, sha256 = recording.original_object_key, recording.sha256_original
    container = PurePosixPath(key).suffix.lstrip(".")
    if container not in ffmpeg.DEMUXERS:
        raise JobError("unknown_container", retryable=False)
    db.rollback()  # the slow part below must not hold a database connection

    with tempfile.TemporaryDirectory(prefix="lkd-job-") as folder:
        path = Path(folder) / "input"
        _download(store, key, sha256, path)
        found, verdict, duration_ms = _inspect(path, container, settings)
    if isinstance(verdict, AudioInfo):
        _promote(store, key, sha256)

    recording = _recording(db, context.target_id, lock=True)
    if recording.upload_status != "quarantined":
        return JobResult(output_summary={"skipped": recording.upload_status})
    recording.detected_container = found.format_name if found else None
    recording.duration_ms = duration_ms
    summary: dict[str, Any]
    if isinstance(verdict, AudioInfo):
        recording.detected_codec = verdict.codec
        recording.sample_rate_hz = verdict.sample_rate_hz
        recording.channels = verdict.channels
        recording.bit_depth = verdict.bit_depth
        recording.is_lossy_source = verdict.is_lossy
        recording.upload_status = "promoted"
        summary = {"outcome": "promoted", "codec": verdict.codec, "duration_ms": duration_ms}
    else:
        recording.upload_status = "rejected_invalid"
        recording.validation_errors = {"code": verdict.code, "reason": verdict.reason}
        submission = db.scalar(
            select(Submission).where(Submission.id == recording.submission_id).with_for_update()
        )
        if submission is not None and submission.status == "processing":
            submission.status = "rejected_invalid"
            submission.updated_at = utcnow()
        summary = {"outcome": "rejected", "code": verdict.code, "reason": verdict.reason}
    queue.enqueue(
        db,
        "cleanup.quarantine",
        target_type="recording",
        target_id=recording.id,
        dedupe_key=f"cleanup.quarantine:{recording.id}",
    )
    return JobResult(
        output_summary=summary,
        tool_versions=ffmpeg.versions(),
        input_sha256=sha256,
    )


@handler("cleanup.quarantine")
def remove_quarantine_copy(context: JobContext) -> JobResult:
    """Deletes a decided upload from quarantine. A promoted one only once originals has it."""
    store = get_object_store()
    recording = _recording(context.db, context.target_id)
    key = recording.original_object_key
    if recording.upload_status == "quarantined":
        return JobResult(output_summary={"skipped": "quarantined"})
    if recording.upload_status == "promoted" and store.head(Bucket.ORIGINALS, key) is None:
        raise JobError("original_missing", retryable=False)
    store.delete(Bucket.QUARANTINE, key)
    return JobResult(output_summary={"deleted": True})
