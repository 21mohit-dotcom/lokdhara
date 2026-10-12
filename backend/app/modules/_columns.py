"""Column helpers shared by module models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, server_default=text("uuidv7()"))


def now_default() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


def fk(target: str) -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey(target))


def optional_fk(target: str) -> Mapped[uuid.UUID | None]:
    return mapped_column(ForeignKey(target))
