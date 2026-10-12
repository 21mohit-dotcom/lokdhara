"""Recording uploads into quarantine (docs/SYSTEM_ARCHITECTURE.md §4.1,
docs/PRIVACY_AND_SECURITY.md §4). Uploaded bytes are generated, never real audio."""

import hashlib
import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings
from app.modules.speakers.models import Speaker
from app.modules.submissions import uploads
from app.modules.submissions.models import Recording, Submission
from app.object_store import Bucket, ObjectStore
from tests.conftest import MakeUser, act_as, requires_postgres
from tests.submission_helpers import FAKE_WEBM, create_draft, give_consent, own_speaker, upload

pytestmark = requires_postgres


@pytest.fixture
def speaker_id(client: TestClient, make_user: MakeUser, db: Session) -> str:
    act_as(client, make_user("asha", "contributor"))
    speaker = own_speaker(client)
    give_consent(client, db, speaker)
    return speaker


@pytest.fixture
def draft_id(client: TestClient, speaker_id: str) -> str:
    return str(create_draft(client, speaker_id)["id"])


def _quarantined(tmp_path: Path) -> list[Path]:
    return [p for p in (tmp_path / "objects" / "test-quarantine").rglob("*") if p.is_file()]


def test_an_upload_lands_in_quarantine_under_a_server_key(
    client: TestClient, draft_id: str, db: Session, object_store: ObjectStore
) -> None:
    response = upload(client, draft_id, filename="Sita Munda village song.WEBM")
    assert response.status_code == 202, response.text
    assert response.json()["upload_status"] == "quarantined"

    recording = db.get(Recording, uuid.UUID(response.json()["recording_id"]))
    assert recording is not None
    key = recording.original_object_key
    assert re.fullmatch(rf"\d{{4}}/\d{{2}}/{recording.id}/original\.webm", key)
    assert recording.sha256_original == hashlib.sha256(FAKE_WEBM).hexdigest()
    assert recording.size_bytes == len(FAKE_WEBM)
    assert recording.original_filename_ext == ".webm"  # never the name itself
    assert recording.recorded_device_hint == "browser_recorder"
    assert object_store.head(Bucket.QUARANTINE, key) == len(FAKE_WEBM)
    assert object_store.head(Bucket.ORIGINALS, key) is None  # promotion is the worker's job

    detail = client.get(f"/api/v1/submissions/{draft_id}").json()
    assert [r["id"] for r in detail["recordings"]] == [str(recording.id)]
    assert detail["status"] == "draft"


def test_a_retried_upload_is_stored_once(client: TestClient, draft_id: str, tmp_path: Path) -> None:
    key = str(uuid.uuid4())
    first = upload(client, draft_id, key=key)
    again = upload(client, draft_id, key=key)
    assert again.status_code == 202
    assert again.json() == first.json()
    assert len(_quarantined(tmp_path)) == 1
    other = upload(client, draft_id)
    assert other.json()["code"] == "recording_exists"


def test_files_that_are_not_audio_are_refused(
    client: TestClient, draft_id: str, tmp_path: Path
) -> None:
    for content in (b"%PDF-1.7 not audio", b"<html><script>", b""):
        response = upload(client, draft_id, content=content, filename="song.webm")
        assert response.status_code == 415
        assert response.json()["code"] == "bad_signature"
    assert _quarantined(tmp_path) == []


def test_oversized_uploads_are_refused_and_not_kept(
    client: TestClient, draft_id: str, settings: Settings, tmp_path: Path
) -> None:
    settings.max_upload_bytes = 32
    response = upload(client, draft_id)
    assert response.status_code == 413
    assert response.json()["code"] == "too_large"
    assert _quarantined(tmp_path) == []


def test_uploads_need_consent_first(
    client: TestClient, make_user: MakeUser, tmp_path: Path
) -> None:
    act_as(client, make_user("asha", "contributor"))
    draft = create_draft(client, own_speaker(client))
    response = upload(client, draft["id"])
    assert response.json()["code"] == "consent_required"
    assert _quarantined(tmp_path) == []


def test_only_the_owner_uploads_and_only_to_audio_drafts(
    client: TestClient, speaker_id: str, draft_id: str, make_user: MakeUser
) -> None:
    text_draft = create_draft(client, speaker_id, kind="text", recording_mode=None)
    assert upload(client, text_draft["id"]).json()["code"] == "recording_not_expected"
    act_as(client, make_user("ravi", "contributor"))
    assert upload(client, draft_id).json()["code"] == "submission_not_found"
    act_as(client, make_user("admin", "admin"))
    assert upload(client, draft_id).json()["code"] == "forbidden"


def test_withdrawn_speakers_cannot_upload(
    client: TestClient, speaker_id: str, draft_id: str, db: Session
) -> None:
    speaker = db.get(Speaker, uuid.UUID(speaker_id))
    assert speaker is not None
    speaker.status = "withdrawn"
    db.commit()
    assert upload(client, draft_id).json()["code"] == "speaker_withdrawn"


def test_uploads_are_rate_limited_per_person(
    client: TestClient, speaker_id: str, settings: Settings
) -> None:
    settings.uploads_per_user_per_hour = 1
    assert upload(client, create_draft(client, speaker_id)["id"]).status_code == 202
    limited = upload(client, create_draft(client, speaker_id)["id"])
    assert limited.status_code == 429
    assert limited.json()["code"] == "upload_rate_limited"
    assert 0 < int(limited.headers["Retry-After"]) <= 3600


def test_the_upload_key_is_required(client: TestClient, draft_id: str) -> None:
    response = client.post(
        f"/api/v1/submissions/{draft_id}/recordings",
        files={"file": ("a.webm", FAKE_WEBM, "audio/webm")},
    )
    assert response.status_code == 422


def test_audio_is_removed_when_the_recording_cannot_be_saved(
    client: TestClient, draft_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checks = uploads._check_accepts_audio
    calls: list[int] = []

    def check_then_fail(db: Session, submission: Submission) -> None:
        calls.append(1)
        if len(calls) == 2:  # the re-check after the file was stored
            raise RuntimeError("database went away")
        checks(db, submission)

    monkeypatch.setattr(uploads, "_check_accepts_audio", check_then_fail)
    with pytest.raises(RuntimeError):
        upload(client, draft_id)
    assert _quarantined(tmp_path) == []


def test_client_filenames_are_not_logged(
    client: TestClient, draft_id: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("DEBUG")
    assert upload(client, draft_id, filename="Sita Munda.webm").status_code == 202
    assert "Sita" not in caplog.text
