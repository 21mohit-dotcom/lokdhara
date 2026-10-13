"""Submitting a draft for processing (docs/USER_FLOWS.md F1, docs/DATA_LIFECYCLE.md stage 1)."""

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.processing import queue
from app.modules.processing.models import Job
from app.modules.prompts.models import Prompt
from app.modules.submissions.models import Recording, Submission, TextLayer, TextRevision
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


def _submit(client: TestClient, submission_id: str) -> dict[str, object]:
    response = client.post(f"{SUBMISSIONS}/{submission_id}/submit")
    result: dict[str, object] = response.json()
    return result


def _jobs(db: Session) -> list[tuple[str, str | None]]:
    return [(job.job_type, job.target_type) for job in db.scalars(select(Job).order_by(Job.id))]


def test_submitting_attaches_consent_and_queues_validation(
    client: TestClient, speaker_id: str, db: Session
) -> None:
    draft = create_draft(client, speaker_id)
    recording_id = upload(client, draft["id"]).json()["recording_id"]
    submitted = _submit(client, draft["id"])
    assert submitted["status"] == "processing"
    assert submitted["has_consent"] is True
    assert submitted["submitted_at"] is not None

    job = db.scalars(select(Job)).one()
    assert (job.job_type, job.target_id) == ("audio.validate", uuid.UUID(recording_id))
    assert _submit(client, draft["id"])["code"] == "submission_not_draft"
    patched = client.patch(f"{SUBMISSIONS}/{draft['id']}", json={"title": "late"})
    assert patched.json()["code"] == "submission_not_editable"


def test_audio_drafts_need_their_recording(client: TestClient, speaker_id: str) -> None:
    draft = create_draft(client, speaker_id)
    assert _submit(client, draft["id"])["code"] == "recording_required"


def test_text_drafts_need_text(client: TestClient, speaker_id: str) -> None:
    draft = create_draft(client, speaker_id, kind="text", recording_mode=None)
    assert _submit(client, draft["id"])["code"] == "text_required"


def test_consent_must_still_be_active_at_submit(
    client: TestClient, make_user: MakeUser, db: Session
) -> None:
    act_as(client, make_user("asha", "contributor"))
    speaker = own_speaker(client)
    draft = create_draft(client, speaker)
    assert _submit(client, draft["id"])["code"] == "consent_required"
    stored = db.get(Submission, uuid.UUID(draft["id"]))
    assert stored is not None and stored.status == "draft"


def test_a_lost_quarantine_file_blocks_submit(
    client: TestClient, speaker_id: str, tmp_path: Path
) -> None:
    draft = create_draft(client, speaker_id)
    upload(client, draft["id"])
    for path in (tmp_path / "objects" / "test-quarantine").rglob("*"):
        if path.is_file():
            path.unlink()
    assert _submit(client, draft["id"])["code"] == "recording_missing"


def test_only_the_owner_submits(client: TestClient, speaker_id: str, make_user: MakeUser) -> None:
    draft = create_draft(client, speaker_id)
    upload(client, draft["id"])
    act_as(client, make_user("admin", "admin"))
    assert _submit(client, draft["id"])["code"] == "forbidden"


def test_read_speech_gets_the_sentence_as_an_unverified_transcription(
    client: TestClient, speaker_id: str, make_user: MakeUser, db: Session
) -> None:
    admin = make_user("admin", "admin").id
    prompt = Prompt(
        prompt_key="test-read",
        version=1,
        prompt_type="read_sentence",
        text="एक छोटा वाक्य।",
        text_language_tag="hi",
        script_code="Deva",
        source_and_licence="test",
        status="approved",
        approved_by=admin,
        created_by=admin,
    )
    db.add(prompt)
    db.commit()
    draft = create_draft(client, speaker_id, recording_mode="read", prompt_id=str(prompt.id))
    recording_id = upload(client, draft["id"]).json()["recording_id"]

    submitted = _submit(client, draft["id"])
    layers = submitted["text_layers"]
    assert isinstance(layers, list) and len(layers) == 1
    layer = layers[0]
    assert (layer["layer_type"], layer["recording_id"], layer["script_code"]) == (
        "transcription",
        recording_id,
        "Deva",
    )
    revision = layer["current_revision"]
    assert revision["content"] == "एक छोटा वाक्य।"
    assert (revision["origin"], revision["verification_status"]) == ("prompt_text", "unverified")
    assert (revision["detected_scripts"], layer["script_mismatch"]) == (["Deva"], False)
    assert sorted(_jobs(db)) == [("audio.validate", "recording"), ("text.derive", "submission")]


def test_submit_is_all_or_nothing(
    client: TestClient, speaker_id: str, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = create_draft(client, speaker_id)
    upload(client, draft["id"])

    def broken(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(queue, "enqueue", broken)
    with pytest.raises(RuntimeError):
        _submit(client, draft["id"])
    db.expire_all()
    stored = db.get(Submission, uuid.UUID(draft["id"]))
    assert stored is not None
    assert (stored.status, stored.consent_record_id) == ("draft", None)
    assert db.scalars(select(TextLayer)).all() == []
    assert db.scalars(select(TextRevision)).all() == []
    assert len(db.scalars(select(Recording)).all()) == 1
