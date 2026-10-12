"""Consent forms and consent records (ADR-012, docs/CONSENT_AND_DATA_GOVERNANCE.md §3)."""

import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.consents.models import ConsentRecord


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
