"""Submissions (docs/API_SPECIFICATION.md §4)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Header, Query, UploadFile, status

from app.db import DbSession
from app.modules.identity.deps import CurrentUser, SettingsDep, require_roles
from app.modules.identity.service import AuthenticatedUser
from app.modules.speakers.service import SELF_SPEAKER_ROLES
from app.modules.submissions import service, text_layers, uploads
from app.modules.submissions.models import Submission, TextRevision
from app.modules.submissions.schemas import (
    CollectionContext,
    DeviceHint,
    RecordingOut,
    RevisionCreateRequest,
    RevisionListOut,
    RevisionOut,
    SubmissionCreateRequest,
    SubmissionDetailOut,
    SubmissionListOut,
    SubmissionOut,
    SubmissionStatus,
    SubmissionUpdateRequest,
    TextLayerCreateRequest,
    TextLayerOut,
    UploadOut,
)
from app.object_store import ObjectStore, get_object_store

router = APIRouter(tags=["submissions"])

Recorder = Annotated[AuthenticatedUser, Depends(require_roles(*SELF_SPEAKER_ROLES))]
Store = Annotated[ObjectStore, Depends(get_object_store)]


def _out(submission: Submission) -> SubmissionOut:
    computed = {"collection_context", "has_consent"}
    fields = {f: getattr(submission, f) for f in SubmissionOut.model_fields if f not in computed}
    return SubmissionOut(
        **fields,
        collection_context=CollectionContext.model_validate(submission.collection_context),
        has_consent=submission.consent_record_id is not None,
    )


def _revision_out(revision: TextRevision) -> RevisionOut:
    computed = {"content"}
    fields = {f: getattr(revision, f) for f in RevisionOut.model_fields if f not in computed}
    # Always the text exactly as written; derived forms stay internal for now.
    return RevisionOut(**fields, content=revision.content_original)


def _layer_out(view: service.LayerView) -> TextLayerOut:
    computed = {"current_revision", "source_changed"}
    fields = {f: getattr(view.layer, f) for f in TextLayerOut.model_fields if f not in computed}
    return TextLayerOut(
        **fields,
        current_revision=_revision_out(view.current) if view.current else None,
        source_changed=view.source_changed,
    )


def _detail(db: DbSession, submission: Submission) -> SubmissionDetailOut:
    recordings = [
        RecordingOut.model_validate(r, from_attributes=True)
        for r in service.recordings_of(db, submission.id)
    ]
    layers = [_layer_out(view) for view in service.text_layers_of(db, submission.id)]
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


@router.post("/submissions/{submission_id}/recordings", status_code=status.HTTP_202_ACCEPTED)
def upload_recording(
    submission_id: uuid.UUID,
    user: Recorder,
    db: DbSession,
    settings: SettingsDep,
    store: Store,
    file: UploadFile,
    idempotency_key: Annotated[uuid.UUID, Header(alias="Idempotency-Key")],
    source: Annotated[DeviceHint | None, Form()] = None,
) -> UploadOut:
    """Multipart `file`, plus `source` (`browser_recorder` or `file_upload`). Send the same
    `Idempotency-Key` with every retry of the same file."""
    recording = uploads.upload_recording(
        db,
        store,
        settings,
        user=user,
        submission_id=submission_id,
        upload_key=idempotency_key,
        stream=file.file,
        filename=file.filename,
        device_hint=source,
    )
    return UploadOut(recording_id=recording.id, upload_status=recording.upload_status)


@router.post("/submissions/{submission_id}/submit")
def submit_submission(
    submission_id: uuid.UUID, user: Recorder, db: DbSession, store: Store
) -> SubmissionDetailOut:
    submission = service.submit(db, store, user=user, submission_id=submission_id)
    return _detail(db, submission)


@router.post("/submissions/{submission_id}/text-layers", status_code=status.HTTP_201_CREATED)
def create_text_layer(
    submission_id: uuid.UUID, body: TextLayerCreateRequest, user: Recorder, db: DbSession
) -> TextLayerOut:
    view = text_layers.create_layer(db, user=user, submission_id=submission_id, body=body)
    return _layer_out(view)


@router.get("/text-layers/{layer_id}")
def get_text_layer(layer_id: uuid.UUID, user: CurrentUser, db: DbSession) -> TextLayerOut:
    return _layer_out(text_layers.get_layer(db, user, layer_id))


@router.get("/text-layers/{layer_id}/revisions")
def list_revisions(layer_id: uuid.UUID, user: CurrentUser, db: DbSession) -> RevisionListOut:
    """Newest first."""
    return RevisionListOut(
        items=[_revision_out(r) for r in text_layers.history(db, user, layer_id)]
    )


@router.post("/text-layers/{layer_id}/revisions", status_code=status.HTTP_201_CREATED)
def add_revision(
    layer_id: uuid.UUID, body: RevisionCreateRequest, user: Recorder, db: DbSession
) -> TextLayerOut:
    """Returns the layer with its new current revision."""
    return _layer_out(text_layers.add_revision(db, user=user, layer_id=layer_id, body=body))
