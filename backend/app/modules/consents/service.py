"""Consent forms and consent records (ADR-012, docs/CONSENT_AND_DATA_GOVERNANCE.md §3)."""

import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import ApiError
from app.modules.consents.dev_forms import DEV_FORMS, FORM_CODE, VERSION
from app.modules.consents.models import ConsentForm, ConsentRecord
from app.modules.identity.service import utcnow


def current_form(db: Session, settings: Settings, language: str) -> ConsentForm:
    query = (
        select(ConsentForm)
        .where(
            ConsentForm.language == language,
            ConsentForm.retired_at.is_(None),
            ConsentForm.effective_from <= utcnow(),
        )
        .order_by(ConsentForm.effective_from.desc())
        .limit(1)
    )
    if settings.env == "production":
        query = query.where(ConsentForm.is_test_form.is_(False))
    form = db.scalar(query)
    if form is None:
        raise ApiError(
            404, "consent_form_not_found", "No consent form is available in this language."
        )
    return form


def ensure_dev_forms(db: Session) -> list[str]:
    """Adds the test forms that are missing; returns their languages. Caller commits."""
    added = []
    for dev_form in DEV_FORMS:
        exists = db.scalar(
            select(ConsentForm.id).where(
                ConsentForm.form_code == FORM_CODE,
                ConsentForm.version == VERSION,
                ConsentForm.language == dev_form.language,
            )
        )
        if exists is None:
            db.add(
                ConsentForm(
                    form_code=FORM_CODE,
                    version=VERSION,
                    language=dev_form.language,
                    body_markdown=dev_form.body_markdown,
                    text_sha256=dev_form.text_sha256,
                    is_test_form=True,
                )
            )
            added.append(dev_form.language)
    return added


def active_consent(db: Session, speaker_id: uuid.UUID) -> ConsentRecord | None:
    return db.scalar(
        select(ConsentRecord).where(
            ConsentRecord.speaker_id == speaker_id, ConsentRecord.status == "active"
        )
    )


def speakers_with_active_consent(db: Session, speaker_ids: Iterable[uuid.UUID]) -> set[uuid.UUID]:
    ids = list(speaker_ids)
    if not ids:
        return set()
    return set(
        db.scalars(
            select(ConsentRecord.speaker_id).where(
                ConsentRecord.speaker_id.in_(ids), ConsentRecord.status == "active"
            )
        )
    )
