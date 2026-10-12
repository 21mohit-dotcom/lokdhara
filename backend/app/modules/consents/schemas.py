import uuid

from pydantic import BaseModel


class ConsentFormOut(BaseModel):
    id: uuid.UUID
    form_code: str
    version: str
    language: str
    body_markdown: str
    text_sha256: str
    is_test_form: bool
    ethics_reference: str | None
