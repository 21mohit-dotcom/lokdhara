"""Text layers and revisions (docs/TEXT_PROCESSING_PIPELINE.md, docs/API_SPECIFICATION.md §6).

Sample text is synthetic Hindi or English, never collected community text.
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.modules.processing import (
    handlers,  # noqa: F401 - registers text.derive
    queue,
)
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


def _revise(client: TestClient, layer: dict[str, Any], content: str, **fields: Any) -> Any:
    body = {"base_revision_id": layer["current_revision"]["id"], "content": content, **fields}
    return client.post(f"/api/v1/text-layers/{layer['id']}/revisions", json=body)


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
    assert stored.detected_scripts == ["Deva", "Latn"]
    assert revision["detected_scripts"] == ["Deva", "Latn"]
    assert layer["script_mismatch"] is False


def test_a_script_other_than_the_chosen_one_is_a_warning_not_a_correction(
    client: TestClient, text_draft: str
) -> None:
    layer = _created(_layer(client, text_draft, script_code="Deva", content="Johar"))
    assert layer["current_revision"]["content"] == "Johar"
    assert layer["current_revision"]["detected_scripts"] == ["Latn"]
    assert (layer["script_code"], layer["script_mismatch"]) == ("Deva", True)

    fixed = _revise(client, layer, "जोहार")
    assert fixed.status_code == 201, fixed.text
    assert fixed.json()["script_mismatch"] is False


def test_text_submissions_can_be_submitted_once_they_have_text(
    client: TestClient, text_draft: str, db: Session
) -> None:
    _created(_layer(client, text_draft))
    submitted = client.post(f"{SUBMISSIONS}/{text_draft}/submit").json()
    assert submitted["status"] == "processing"
    assert [job.job_type for job in db.scalars(select(Job))] == ["text.derive"]
    late = _layer(client, text_draft, content="और एक")
    assert late.json()["code"] == "submission_not_editable"


def _accepted(client: TestClient, text_draft: str, engine: Engine) -> dict[str, Any]:
    layer = _created(_layer(client, text_draft))
    assert client.post(f"{SUBMISSIONS}/{text_draft}/submit").status_code == 200
    while queue.process_one(engine, "test-worker", 60):
        pass
    assert client.get(f"{SUBMISSIONS}/{text_draft}").json()["status"] == "accepted"
    return layer


def test_contributors_correct_and_translate_their_text_after_acceptance(
    client: TestClient, text_draft: str, engine: Engine, db: Session
) -> None:
    layer = _accepted(client, text_draft, engine)
    corrected = _created(_revise(client, layer, "यह सुधारा हुआ वाक्य है।"))
    assert corrected["current_revision"]["revision_number"] == 2
    translation = _layer(
        client,
        text_draft,
        layer_type="translation",
        entry_type=None,
        source_layer_id=layer["id"],
        language_tag="en",
        script_code="Latn",
        content="This is a corrected sentence.",
    )
    _created(translation)

    # The changed text is checked again, once, and the submission stays accepted.
    queued = db.scalars(select(Job).where(Job.status == "queued")).all()
    assert [job.job_type for job in queued] == ["text.derive"]
    while queue.process_one(engine, "test-worker", 60):
        pass
    assert client.get(f"{SUBMISSIONS}/{text_draft}").json()["status"] == "accepted"


def test_withdrawn_submissions_cannot_be_edited(
    client: TestClient, text_draft: str, engine: Engine, db: Session
) -> None:
    layer = _accepted(client, text_draft, engine)
    db.execute(
        text("UPDATE submissions SET status = 'withdrawn' WHERE id = :id"), {"id": text_draft}
    )
    db.commit()
    assert _revise(client, layer, "बदलाव").json()["code"] == "text_layer_not_found"


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


# ------------------------------------------------------------------ revisions


def test_edits_are_new_revisions_on_top_of_the_one_edited(
    client: TestClient, text_draft: str, db: Session
) -> None:
    first = _created(_layer(client, text_draft))
    second = _created(_revise(client, first, "यह बदला हुआ वाक्य है।", change_note="typo"))
    revision = second["current_revision"]
    assert revision["revision_number"] == 2
    assert revision["based_on_revision_id"] == first["current_revision"]["id"]
    assert revision["change_note"] == "typo"

    history = client.get(f"/api/v1/text-layers/{first['id']}/revisions").json()["items"]
    assert [r["revision_number"] for r in history] == [2, 1]
    original = db.get(TextRevision, uuid.UUID(first["current_revision"]["id"]))
    assert original is not None and original.content_original == "यह एक परीक्षण वाक्य है।"


def test_an_edit_from_an_old_revision_is_refused(client: TestClient, text_draft: str) -> None:
    first = _created(_layer(client, text_draft))
    _created(_revise(client, first, "पहला बदलाव"))
    stale = _revise(client, first, "दूसरा बदलाव")
    assert stale.status_code == 409
    assert stale.json()["code"] == "revision_conflict"


def test_translations_show_when_their_source_changed(client: TestClient, text_draft: str) -> None:
    source = _created(_layer(client, text_draft))
    english = _created(
        _layer(
            client,
            text_draft,
            layer_type="translation",
            entry_type=None,
            source_layer_id=source["id"],
            language_tag="en",
            script_code="Latn",
            content="A test sentence.",
        )
    )
    _created(_revise(client, source, "यह नया वाक्य है।"))
    stale = client.get(f"/api/v1/text-layers/{english['id']}").json()
    assert stale["source_changed"] is True
    detail = client.get(f"{SUBMISSIONS}/{text_draft}").json()
    assert [layer["source_changed"] for layer in detail["text_layers"]] == [False, True]
    refreshed = _created(_revise(client, stale, "A new sentence."))
    assert refreshed["source_changed"] is False


# ------------------------------------------------------------------ who may see and edit


def test_only_the_owner_edits_and_only_visible_text_is_shown(
    client: TestClient, text_draft: str, make_user: MakeUser
) -> None:
    layer = _created(_layer(client, text_draft))
    path = f"/api/v1/text-layers/{layer['id']}"

    act_as(client, make_user("ravi", "contributor"))
    assert client.get(path).json()["code"] == "text_layer_not_found"
    assert client.get(f"{path}/revisions").status_code == 404
    assert _revise(client, layer, "x").status_code == 404
    assert _layer(client, text_draft).status_code == 404

    act_as(client, make_user("admin", "admin"))
    assert client.get(path).status_code == 200
    assert _revise(client, layer, "x").json()["code"] == "forbidden"
    assert client.get(f"/api/v1/text-layers/{uuid.uuid4()}").status_code == 404
