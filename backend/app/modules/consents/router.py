"""Consent forms and consent records (docs/API_SPECIFICATION.md §3)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, UploadFile, status

from app.db import DbSession
from app.forms import parse_json_field
from app.modules.consents import service
from app.modules.consents.models import ConsentRecord
from app.modules.consents.schemas import (
    ConsentFormOut,
    ConsentListOut,
    ConsentOut,
    ConsentRequest,
)
from app.modules.identity.deps import Context, CurrentUser, SettingsDep
from app.object_store import ObjectStore, get_object_store

router = APIRouter(tags=["consent"])

Store = Annotated[ObjectStore, Depends(get_object_store)]


def _out(record: ConsentRecord) -> ConsentOut:
    fields = {f: getattr(record, f) for f in ConsentOut.model_fields if f != "has_evidence"}
    # The evidence key and paper reference are restricted; only their presence is shown.
    return ConsentOut(**fields, has_evidence=record.evidence_object_key is not None)


@router.get("/consent-forms/current")
def current_form(
    _user: CurrentUser,
    db: DbSession,
    settings: SettingsDep,
    language: Annotated[str, Query(pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")] = "hi",
) -> ConsentFormOut:
    form = service.current_form(db, settings, language)
    return ConsentFormOut.model_validate(form, from_attributes=True)


@router.post("/speakers/{speaker_id}/consents", status_code=status.HTTP_201_CREATED)
def record_consent(
    speaker_id: uuid.UUID,
    consent: Annotated[str, Form(description="ConsentRequest as JSON")],
    user: CurrentUser,
    db: DbSession,
    settings: SettingsDep,
    store: Store,
    context: Context,
    evidence: UploadFile | None = None,
) -> ConsentOut:
    """Multipart: the answers as JSON in `consent`; oral consent adds the recording as
    `evidence`."""
    body = parse_json_field(ConsentRequest, consent, "consent")
    record = service.record_consent(
        db,
        store,
        settings,
        actor=user,
        speaker_id=speaker_id,
        body=body,
        evidence=evidence.file if evidence else None,
        context=context,
    )
    return _out(record)


@router.get("/speakers/{speaker_id}/consents")
def consent_history(speaker_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ConsentListOut:
    return ConsentListOut(items=[_out(r) for r in service.history(db, user, speaker_id)])
