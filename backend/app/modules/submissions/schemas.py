import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.languages import LanguageTag
from app.text_input import MultiLine, SingleLine

Kind = Literal["audio", "text", "audio_text"]
ContentType = Literal["story", "conversation", "vocabulary", "song", "sentence_list", "other"]
RecordingMode = Literal["free", "prompted", "read"]
CollectionMethod = Literal[
    "self_recorded", "facilitator_field", "facilitator_remote", "imported_archive"
]
SubmissionStatus = Literal[
    "draft",
    "uploading",
    "processing",
    "processing_failed",
    "rejected_invalid",
    "awaiting_review",
    "in_review",
    "changes_requested",
    "approved",
    "rejected",
    "withdrawn",
]
DeviceHint = Literal["browser_recorder", "file_upload"]


class CollectionContext(BaseModel):
    """The allow-listed keys of docs/DATA_DICTIONARY.md §3; anything else is rejected."""

    model_config = ConfigDict(extra="forbid")

    setting: Literal["indoor_quiet", "indoor_noisy", "outdoor", "unknown"] | None = None
    speaker_count: int | None = Field(default=None, ge=1, le=50)
    equipment: (
        Literal["phone_builtin_mic", "phone_external_mic", "field_recorder", "unknown"] | None
    ) = None
    # Never exported: it may contain personal details.
    notes: MultiLine | None = Field(default=None, max_length=500)


def _not_in_future(value: date | None) -> None:
    # A day of slack: India is ahead of UTC, so "today" there can be tomorrow in UTC.
    if value is not None and value > datetime.now(UTC).date() + timedelta(days=1):
        raise ValueError("recorded_on cannot be in the future")


class SubmissionCreateRequest(BaseModel):
    """`client_submission_id` is generated on the device; sending it again returns the same
    draft, so a retry after a lost response never creates a second one."""

    client_submission_id: uuid.UUID
    speaker_id: uuid.UUID
    kind: Kind
    content_type: ContentType
    title: SingleLine | None = Field(default=None, max_length=200)
    language_tag: LanguageTag = "unr"
    dialect_label: SingleLine | None = Field(default=None, max_length=100)
    region_coarse: SingleLine | None = Field(default=None, max_length=100)
    recorded_on: date | None = None
    collection_method: CollectionMethod
    recording_mode: RecordingMode | None = None
    prompt_id: uuid.UUID | None = None
    collection_context: CollectionContext = Field(default_factory=CollectionContext)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if (self.kind == "text") != (self.recording_mode is None):
            raise ValueError("recording_mode is required for audio, and only for audio")
        if (self.recording_mode in ("prompted", "read")) != (self.prompt_id is not None):
            raise ValueError("prompt_id is required for prompted and read speech, and only then")
        _not_in_future(self.recorded_on)
        return self


class SubmissionUpdateRequest(BaseModel):
    """Descriptive metadata only. What was recorded, of whom, and how is fixed at creation."""

    content_type: ContentType | None = None
    title: SingleLine | None = Field(default=None, max_length=200)
    dialect_label: SingleLine | None = Field(default=None, max_length=100)
    region_coarse: SingleLine | None = Field(default=None, max_length=100)
    recorded_on: date | None = None
    collection_context: CollectionContext | None = None

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if "content_type" in self.model_fields_set and self.content_type is None:
            raise ValueError("content_type cannot be removed")
        _not_in_future(self.recorded_on)
        return self


class RecordingOut(BaseModel):
    id: uuid.UUID
    upload_status: str
    size_bytes: int
    duration_ms: int | None
    quality_flags: list[str]
    created_at: datetime


class RevisionOut(BaseModel):
    id: uuid.UUID
    revision_number: int
    content: str
    origin: str
    verification_status: str
    created_at: datetime


class TextLayerOut(BaseModel):
    id: uuid.UUID
    layer_type: str
    recording_id: uuid.UUID | None
    source_layer_id: uuid.UUID | None
    entry_type: str | None
    language_tag: str
    script_code: str
    current_revision: RevisionOut | None


class SubmissionOut(BaseModel):
    id: uuid.UUID
    client_submission_id: uuid.UUID
    speaker_id: uuid.UUID
    kind: Kind
    content_type: ContentType
    title: str | None
    language_tag: str
    dialect_label: str | None
    region_coarse: str | None
    recorded_on: date | None
    collection_method: CollectionMethod
    recording_mode: RecordingMode | None
    prompt_id: uuid.UUID | None
    collection_context: CollectionContext
    status: SubmissionStatus
    has_consent: bool
    created_at: datetime
    submitted_at: datetime | None
    updated_at: datetime


class SubmissionDetailOut(SubmissionOut):
    recordings: list[RecordingOut]
    text_layers: list[TextLayerOut]


class SubmissionListOut(BaseModel):
    items: list[SubmissionOut]
    next_cursor: str | None


class UploadOut(BaseModel):
    recording_id: uuid.UUID
    upload_status: str
