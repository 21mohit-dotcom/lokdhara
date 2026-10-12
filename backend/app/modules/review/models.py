"""docs/DATABASE_SCHEMA.md §4. Created by migration 0007."""

import uuid
from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.modules._columns import fk, now_default, optional_fk, uuid_pk


class ReviewEvent(Base):
    """Append-only. A trigger rejects decisions on a reviewer's own submission."""

    __tablename__ = "review_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    submission_id: Mapped[uuid.UUID] = fk("submissions.id")
    text_revision_id: Mapped[uuid.UUID | None] = optional_fk("text_revisions.id")
    reviewer_id: Mapped[uuid.UUID] = fk("users.id")
    action: Mapped[str] = mapped_column(Text)
    reason_code: Mapped[str | None] = mapped_column(Text)
    restriction: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = now_default()
