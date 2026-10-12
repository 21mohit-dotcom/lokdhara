"""Text layers and revisions (docs/TEXT_PROCESSING_PIPELINE.md, docs/API_SPECIFICATION.md §6).

Sample text is synthetic Hindi or English, never collected community text.
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.processing.models import Job
from app.modules.submissions.models import TextRevision
from tests.conftest import MakeUser, TestUser, act_as, requires_postgres
from tests.submission_helpers import SUBMISSIONS, create_draft, give_consent, own_speaker, upload

pytestmark = requires_postgres


@pytest.fixture
def asha(client: TestClient, make_user: MakeUser) -> TestUser:
    user = make_user("asha", "contributor")
    act_as(client, user)
    return user


@pytest.fixture
def speaker_id(client: TestClient, asha: TestUser, db: Session) -> str:
    speaker = own_speaker(client)
    give_consent(client, db, speaker)
    return speaker


@pytest.fixture
def text_draft(client: TestClient, speaker_id: str) -> str:
    return str(create_draft(client, speaker_id, kind="text", recording_mode=None)["id"])


def _layer(client: TestClient, submission_id: str, **fields: Any) -> Any:
    body = {
        "layer_type": "standalone",
        "entry_type": "sentence",
        "language_tag": "unr",
        "script_code": "Deva",
        "content": "यह एक परीक्षण वाक्य है।",
        **fields,
    }
    return client.post(f"{SUBMISSIONS}/{submission_id}/text-layers", json=body)


def _created(response: Any) -> dict[str, Any]:
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


# ------------------------------------------------------------------ storing text


def test_text_is_stored_exactly_as_written(
    client: TestClient, text_draft: str, db: Session
) -> None:
    written = "  क्‍ष é\r\nदूसरी पंक्ति  "
    layer = _created(_layer(client, text_draft, entry_type="paragraph", content=written))
    revision = layer["current_revision"]
    assert revision["content"] == written
    assert (revision["revision_number"], revision["origin"]) == (1, "human_contributor")
    assert revision["verification_status"] == "unverified"

    stored = db.get(TextRevision, uuid.UUID(revision["id"]))
    assert stored is not None
    assert stored.content_original == written
    assert stored.content_nfc == "  क्‍ष é\nदूसरी पंक्ति  "
    assert stored.detected_scripts == []  # filled by the text.derive job (M4)


def test_text_submissions_can_be_submitted_once_they_have_text(
    client: TestClient, text_draft: str, db: Session
) -> None:
    _created(_layer(client, text_draft))
    submitted = client.post(f"{SUBMISSIONS}/{text_draft}/submit").json()
    assert submitted["status"] == "processing"
    assert [job.job_type for job in db.scalars(select(Job))] == ["text.derive"]
    late = _layer(client, text_draft, content="और एक")
    assert late.json()["code"] == "submission_not_editable"


@pytest.mark.parametrize(
    ("fields", "code"),
    [
        ({"content": "छुपा‮पाठ"}, "disallowed_character"),
        ({"content": "a\x00b"}, "disallowed_character"),
        ({"content": " \n "}, "text_empty"),
        ({"entry_type": "word", "content": "क" * 201}, "text_too_long"),
    ],
)
def test_unsafe_text_is_refused_not_repaired(
    client: TestClient, text_draft: str, fields: dict[str, Any], code: str
) -> None:
    response = _layer(client, text_draft, **fields)
    assert response.status_code == 422
    assert response.json()["code"] == code


def test_uncertain_words_are_flagged(client: TestClient, text_draft: str) -> None:
    layer = _created(_layer(client, text_draft, content="वह [?घर] गया"))
    assert layer["current_revision"]["uncertainty_markup"] is True


# ------------------------------------------------------------------ what links to what


def test_layers_must_fit_the_submission(
    client: TestClient, speaker_id: str, text_draft: str
) -> None:
    audio = create_draft(client, speaker_id)["id"]
    assert _layer(client, audio).json()["code"] == "layer_not_allowed"
    # A transcription needs a recording, standalone text an entry type.
    missing_link = _layer(client, text_draft, layer_type="transcription", entry_type=None)
    assert missing_link.status_code == 422
    assert _layer(client, text_draft, entry_type=None).status_code == 422


def test_transcriptions_belong_to_a_recording_of_the_same_submission(
    client: TestClient, speaker_id: str
) -> None:
    first, second = (create_draft(client, speaker_id)["id"] for _ in range(2))
    recording = upload(client, first).json()["recording_id"]

    def transcribe(submission_id: str, **fields: Any) -> Any:
        return _layer(
            client,
            submission_id,
            layer_type="transcription",
            entry_type=None,
            recording_id=recording,
            **fields,
        )

    assert transcribe(second).json()["code"] == "layer_link_invalid"
    layer = _created(transcribe(first))
    assert layer["recording_id"] == recording
    assert transcribe(first).json()["code"] == "layer_exists"
    _created(transcribe(first, script_code="Latn", content="Johar"))  # another script is fine


def test_translations_translate_text_into_another_language(
    client: TestClient, text_draft: str
) -> None:
    source = _created(_layer(client, text_draft))

    def translate(source_id: str, language: str = "en", **fields: Any) -> Any:
        return _layer(
            client,
            text_draft,
            layer_type="translation",
            entry_type=None,
            source_layer_id=source_id,
            language_tag=language,
            script_code="Latn",
            content="This is a test sentence.",
            **fields,
        )

    assert translate(source["id"], language="unr").json()["code"] == "same_language"
    english = _created(translate(source["id"]))
    assert english["current_revision"]["source_revision_id"] == source["current_revision"]["id"]
    assert english["source_changed"] is False
    assert translate(source["id"]).json()["code"] == "layer_exists"
    assert translate(english["id"], language="hi").json()["code"] == "layer_link_invalid"


# ------------------------------------------------------------------ who may see and edit


def test_only_visible_text_is_shown(
    client: TestClient, text_draft: str, make_user: MakeUser
) -> None:
    layer = _created(_layer(client, text_draft))
    path = f"/api/v1/text-layers/{layer['id']}"

    act_as(client, make_user("ravi", "contributor"))
    assert client.get(path).json()["code"] == "text_layer_not_found"
    assert _layer(client, text_draft).status_code == 404

    act_as(client, make_user("admin", "admin"))
    assert client.get(path).status_code == 200
    assert client.get(f"/api/v1/text-layers/{uuid.uuid4()}").status_code == 404
