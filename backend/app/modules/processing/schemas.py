import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class JobOut(BaseModel):
    id: uuid.UUID
    job_type: str
    status: Literal["queued", "running", "succeeded", "failed"]
    attempts: int
    max_attempts: int
    target_type: str | None
    target_id: uuid.UUID | None
    last_error_code: str | None
    run_after: datetime
    created_at: datetime
    finished_at: datetime | None


class JobListOut(BaseModel):
    items: list[JobOut]
