"""Submission drafts and submitting them for processing (docs/USER_FLOWS.md F1).

A draft exists on the device first; the server copy is created when the contributor uploads.
Consent is required before any audio reaches the server and again at submit, when the active
consent record is attached (the database refuses to let a submission leave draft without one).
"""

import unicodedata
import uuid

from sqlalchemy import ColumnElement, and_, or_, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.modules.consents import service as consents
from app.modules.identity.service import AuthenticatedUser, utcnow
from app.modules.processing import queue
from app.modules.prompts import service as prompts
from app.modules.speakers import service as speakers
from app.modules.speakers.models import Speaker
from app.modules.submissions.models import Recording, Submission, TextLayer, TextRevision
from app.modules.submissions.schemas import SubmissionCreateRequest, SubmissionUpdateRequest
from app.object_store import Bucket, ObjectStore

EDITABLE_STATUSES = ("draft", "changes_requested")
AUDIO_KINDS = ("audio", "audio_text")
TEXT_KINDS = ("text", "audio_text")
MAX_PAGE = 100


def _not_found() -> ApiError:
    # Same answer whether the submission does not exist or is not visible to this user.
    return ApiError(404, "submission_not_found", "Submission not found.")


def consent_required() -> ApiError:
    return ApiError(
        422, "consent_required", "The speaker's consent must be recorded before this step."
    )


# ------------------------------------------------------------------ access


def visible_to(user: AuthenticatedUser) -> ColumnElement[bool]:
    """Milestone 3 part of the data-level rule (docs/ACCESS_CONTROL.md §3): people see what
    they submitted, facilitators also see what was recorded of speakers they registered, and
    admins see everything. Reviewer and researcher access arrive with review and datasets."""
    if user.has_role("admin"):
        return true()
    own = Submission.submitted_by == user.id
    if user.has_role("facilitator"):
        own = or_(own, Submission.speaker_id.in_(speakers.created_by(user.id)))
    return and_(Submission.status != "withdrawn", own)


def get_visible(db: Session, user: AuthenticatedUser, submission_id: uuid.UUID) -> Submission:
    submission = db.scalar(
        select(Submission).where(Submission.id == submission_id, visible_to(user))
    )
    if submission is None:
        raise _not_found()
    return submission


def get_owned(
    db: Session, user: AuthenticatedUser, submission_id: uuid.UUID, *, for_update: bool = False
) -> Submission:
    """Only the person who created a submission edits, uploads to, or submits it."""
    query = select(Submission).where(Submission.id == submission_id, visible_to(user))
    if for_update:
        query = query.with_for_update()
    submission = db.scalar(query)
    if submission is None:
        raise _not_found()
    if submission.submitted_by != user.id:
        raise ApiError(403, "forbidden", "Only the person who created it can change this.")
    return submission


# ------------------------------------------------------------------ drafts


def _check_collection_method(user: AuthenticatedUser, speaker: Speaker, method: str) -> None:
    is_self = speaker.linked_user_id == user.id
    allowed = {
        "self_recorded": is_self,
        "facilitator_field": not is_self and user.has_role("facilitator", "admin"),
        "facilitator_remote": not is_self and user.has_role("facilitator", "admin"),
        "imported_archive": user.has_role("admin"),
    }
    if not allowed[method]:
        raise ApiError(
            422,
            "collection_method_not_allowed",
            "This collection method does not fit this speaker or your role.",
        )


def create_draft(
    db: Session, *, user: AuthenticatedUser, body: SubmissionCreateRequest
) -> Submission:
    existing = _by_client_id(db, body.client_submission_id)
    if existing is not None:
        return _replay(existing, user)
    speaker = speakers.get_for_action(db, user, body.speaker_id)
    _check_collection_method(user, speaker, body.collection_method)
    if body.prompt_id is not None and body.recording_mode is not None:
        prompts.get_for_recording(db, body.prompt_id, body.recording_mode)

    submission = Submission(
        **body.model_dump(exclude={"collection_context"}),
        collection_context=body.collection_context.model_dump(exclude_none=True),
        submitted_by=user.id,
    )
    db.add(submission)
    try:
        db.commit()
    except IntegrityError:
        # The same draft sent twice at once: the other request created it.
        db.rollback()
        existing = _by_client_id(db, body.client_submission_id)
        if existing is None:
            raise
        return _replay(existing, user)
    return submission


def _by_client_id(db: Session, client_submission_id: uuid.UUID) -> Submission | None:
    return db.scalar(
        select(Submission).where(Submission.client_submission_id == client_submission_id)
    )


def _replay(existing: Submission, user: AuthenticatedUser) -> Submission:
    if existing.submitted_by != user.id:
        raise ApiError(
            409, "client_submission_id_taken", "This draft ID is already used; make a new one."
        )
    return existing


def list_submissions(
    db: Session,
    user: AuthenticatedUser,
    *,
    mine: bool,
    status: str | None,
    limit: int,
    cursor: uuid.UUID | None,
) -> tuple[list[Submission], uuid.UUID | None]:
    """Newest first. IDs are UUIDv7, so ordering by ID is ordering by creation time."""
    query = select(Submission).where(visible_to(user)).order_by(Submission.id.desc())
    if mine:
        query = query.where(Submission.submitted_by == user.id)
    if status is not None:
        query = query.where(Submission.status == status)
    if cursor is not None:
        query = query.where(Submission.id < cursor)
    rows = list(db.scalars(query.limit(limit + 1)))
    if len(rows) > limit:
        return rows[:limit], rows[limit - 1].id
    return rows, None


def update_draft(
    db: Session, *, user: AuthenticatedUser, submission_id: uuid.UUID, body: SubmissionUpdateRequest
) -> Submission:
    submission = get_owned(db, user, submission_id, for_update=True)
    if submission.status not in EDITABLE_STATUSES:
        raise ApiError(409, "submission_not_editable", "This submission can no longer be edited.")
    changes = body.model_dump(exclude_unset=True, exclude={"collection_context"})
    for field, value in changes.items():
        setattr(submission, field, value)
    if body.collection_context is not None:
        submission.collection_context = body.collection_context.model_dump(exclude_none=True)
    submission.updated_at = utcnow()
    db.commit()
    return submission


def recordings_of(db: Session, submission_id: uuid.UUID) -> list[Recording]:
    return list(
        db.scalars(
            select(Recording)
            .where(Recording.submission_id == submission_id)
            .order_by(Recording.created_at)
        )
    )


def text_layers_of(
    db: Session, submission_id: uuid.UUID
) -> list[tuple[TextLayer, TextRevision | None]]:
    return [
        (layer, revision)
        for layer, revision in db.execute(
            select(TextLayer, TextRevision)
            .outerjoin(TextRevision, TextRevision.id == TextLayer.current_revision_id)
            .where(TextLayer.submission_id == submission_id)
            .order_by(TextLayer.created_at)
        )
    ]


# ------------------------------------------------------------------ submit


def submit(
    db: Session, store: ObjectStore, *, user: AuthenticatedUser, submission_id: uuid.UUID
) -> Submission:
    """Draft → processing. Attaches the speaker's active consent and queues validation."""
    submission = get_owned(db, user, submission_id, for_update=True)
    if submission.status != "draft":
        raise ApiError(409, "submission_not_draft", "Only drafts can be submitted.")
    speaker = speakers.get_for_action(db, user, submission.speaker_id)
    consent = consents.active_consent(db, speaker.id)
    if consent is None:
        raise consent_required()

    recordings = recordings_of(db, submission.id)
    if submission.kind in AUDIO_KINDS and not recordings:
        raise ApiError(422, "recording_required", "Upload the recording before submitting.")
    for recording in recordings:
        if store.head(Bucket.QUARANTINE, recording.original_object_key) is None:
            raise ApiError(
                409, "recording_missing", "The uploaded recording is no longer available."
            )
    has_text = any(revision for _, revision in text_layers_of(db, submission.id))
    if submission.kind in TEXT_KINDS and not has_text:
        raise ApiError(422, "text_required", "Add the text before submitting.")

    if submission.recording_mode == "read" and submission.prompt_id is not None:
        has_text = _add_prompt_text(db, submission, recordings[0]) or has_text

    submission.consent_record_id = consent.id
    submission.status = "processing"
    submission.submitted_at = submission.updated_at = utcnow()
    for recording in recordings:
        queue.enqueue(
            db,
            "audio.validate",
            target_type="recording",
            target_id=recording.id,
            dedupe_key=f"audio.validate:{recording.id}",
        )
    if has_text:
        queue.enqueue(
            db,
            "text.derive",
            target_type="submission",
            target_id=submission.id,
            dedupe_key=f"text.derive:{submission.id}",
        )
    db.commit()
    return submission


def _add_prompt_text(db: Session, submission: Submission, recording: Recording) -> bool:
    """Read speech: the sentence that was read becomes the first transcription, with origin
    `prompt_text` and unverified, because speakers do not always read exactly what is shown.
    Skipped when the contributor already typed a transcription of their own."""
    if submission.prompt_id is None:
        return False
    already = db.scalar(
        select(TextLayer.id)
        .where(TextLayer.recording_id == recording.id, TextLayer.layer_type == "transcription")
        .limit(1)
    )
    prompt = prompts.recorded_prompt(db, submission.prompt_id)
    if already is not None or prompt.text is None or prompt.script_code is None:
        return False
    layer = TextLayer(
        submission_id=submission.id,
        layer_type="transcription",
        recording_id=recording.id,
        language_tag=prompt.text_language_tag or submission.language_tag,
        script_code=prompt.script_code,
    )
    db.add(layer)
    db.flush()
    revision = TextRevision(
        layer_id=layer.id,
        revision_number=1,
        content_original=prompt.text,
        content_nfc=unicodedata.normalize("NFC", prompt.text),
        origin="prompt_text",
    )
    db.add(revision)
    db.flush()
    layer.current_revision_id = revision.id
    return True
