"""Submission drafts (docs/USER_FLOWS.md F1).

A draft exists on the device first; the server copy is created when the contributor uploads.
Consent is required before any audio reaches the server.
"""

import uuid

from sqlalchemy import ColumnElement, and_, or_, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.modules.identity.service import AuthenticatedUser, utcnow
from app.modules.prompts import service as prompts
from app.modules.speakers import service as speakers
from app.modules.speakers.models import Speaker
from app.modules.submissions.models import Recording, Submission, TextLayer, TextRevision
from app.modules.submissions.schemas import SubmissionCreateRequest, SubmissionUpdateRequest

EDITABLE_STATUSES = ("draft", "changes_requested")
AUDIO_KINDS = ("audio", "audio_text")
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
    """Only the person who created a submission edits it or uploads to it."""
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
