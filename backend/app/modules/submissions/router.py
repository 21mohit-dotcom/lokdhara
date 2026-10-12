"""Submissions (docs/API_SPECIFICATION.md §4)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.db import DbSession
from app.modules.identity.deps import CurrentUser, require_roles
from app.modules.identity.service import AuthenticatedUser
from app.modules.speakers.service import SELF_SPEAKER_ROLES
from app.modules.submissions import service
from app.modules.submissions.models import Submission
from app.modules.submissions.schemas import (
    CollectionContext,
    RecordingOut,
    RevisionOut,
    SubmissionCreateRequest,
    SubmissionDetailOut,
    SubmissionListOut,
    SubmissionOut,
    SubmissionStatus,
    SubmissionUpdateRequest,
    TextLayerOut,
)

router = APIRouter(tags=["submissions"])

Recorder = Annotated[AuthenticatedUser, Depends(require_roles(*SELF_SPEAKER_ROLES))]


def _out(submission: Submission) -> SubmissionOut:
    computed = {"collection_context", "has_consent"}
    fields = {f: getattr(submission, f) for f in SubmissionOut.model_fields if f not in computed}
    return SubmissionOut(
        **fields,
        collection_context=CollectionContext.model_validate(submission.collection_context),
        has_consent=submission.consent_record_id is not None,
    )


def _detail(db: DbSession, submission: Submission) -> SubmissionDetailOut:
    recordings = [
        RecordingOut.model_validate(r, from_attributes=True)
        for r in service.recordings_of(db, submission.id)
    ]
    layers = [
        TextLayerOut(
            **{f: getattr(layer, f) for f in TextLayerOut.model_fields if f != "current_revision"},
            current_revision=(
                RevisionOut(
                    id=revision.id,
                    revision_number=revision.revision_number,
                    content=revision.content_original,
                    origin=revision.origin,
                    verification_status=revision.verification_status,
                    created_at=revision.created_at,
                )
                if revision
                else None
            ),
        )
        for layer, revision in service.text_layers_of(db, submission.id)
    ]
    return SubmissionDetailOut(
        **_out(submission).model_dump(), recordings=recordings, text_layers=layers
    )


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
def create_submission(
    body: SubmissionCreateRequest, user: Recorder, db: DbSession
) -> SubmissionDetailOut:
    """Creates a draft, or returns the existing one for a repeated `client_submission_id`."""
    return _detail(db, service.create_draft(db, user=user, body=body))


@router.get("/submissions")
def list_submissions(
    user: CurrentUser,
    db: DbSession,
    mine: bool = True,
    submission_status: Annotated[SubmissionStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=service.MAX_PAGE)] = 50,
    cursor: uuid.UUID | None = None,
) -> SubmissionListOut:
    rows, next_cursor = service.list_submissions(
        db, user, mine=mine, status=submission_status, limit=limit, cursor=cursor
    )
    return SubmissionListOut(
        items=[_out(row) for row in rows],
        next_cursor=str(next_cursor) if next_cursor else None,
    )


@router.get("/submissions/{submission_id}")
def get_submission(
    submission_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> SubmissionDetailOut:
    return _detail(db, service.get_visible(db, user, submission_id))


@router.patch("/submissions/{submission_id}")
def update_submission(
    submission_id: uuid.UUID, body: SubmissionUpdateRequest, user: Recorder, db: DbSession
) -> SubmissionDetailOut:
    submission = service.update_draft(db, user=user, submission_id=submission_id, body=body)
    return _detail(db, submission)
