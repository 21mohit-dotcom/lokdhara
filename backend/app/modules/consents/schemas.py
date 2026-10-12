import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.text_input import MultiLine, SingleLine

Method = Literal["in_app", "oral_recorded", "paper_reference"]
Attribution = Literal["pseudonymous", "name", "none"]


class ConsentFormOut(BaseModel):
    id: uuid.UUID
    form_code: str
    version: str
    language: str
    body_markdown: str
    text_sha256: str
    is_test_form: bool
    ethics_reference: str | None


class ConsentRequest(BaseModel):
    """Sent as multipart form fields; `evidence` (audio) accompanies oral consent.

    Every permission except store-and-review defaults to No
    (docs/CONSENT_AND_DATA_GOVERNANCE.md §3.1).
    """

    consent_form_id: uuid.UUID
    method: Method
    guardian_involved: bool = False
    guardian_relationship: SingleLine | None = Field(default=None, max_length=60)
    paper_reference: SingleLine | None = Field(
        default=None, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9/_.-]*$"
    )
    allow_store_and_review: bool
    allow_research: bool = False
    allow_public_access: bool = False
    allow_ai_training: bool = False
    allow_commercial_use: bool = False
    attribution_preference: Attribution = "pseudonymous"
    demographics_consented: bool = False
    applies_to_past_contributions: bool = False
    notes: MultiLine | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.guardian_relationship is not None and not self.guardian_involved:
            raise ValueError("guardian_relationship needs guardian_involved")
        if (self.method == "paper_reference") != (self.paper_reference is not None):
            raise ValueError("paper_reference is required for, and only for, paper consent")
        return self


class ConsentOut(BaseModel):
    id: uuid.UUID
    speaker_id: uuid.UUID
    consent_form_id: uuid.UUID
    supersedes_id: uuid.UUID | None
    status: str
    method: str
    obtained_at: datetime
    guardian_involved: bool
    has_evidence: bool
    allow_store_and_review: bool
    allow_research: bool
    allow_public_access: bool
    allow_ai_training: bool
    allow_commercial_use: bool
    attribution_preference: str
    demographics_consented: bool
    applies_to_past_contributions: bool


class ConsentListOut(BaseModel):
    items: list[ConsentOut]
