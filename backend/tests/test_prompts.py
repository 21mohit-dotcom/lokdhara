"""The prompt library (ADR-018, docs/RECORDING_MODES.md, docs/API_SPECIFICATION.md §4a)."""

import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditEvent
from app.modules.prompts.models import Prompt
from tests.conftest import MakeUser, TestUser, act_as, requires_postgres

pytestmark = requires_postgres

ADMIN = "/api/v1/admin/prompts"
# First bytes of each format: enough for the format check. Generated, never real media.
FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _situation(key: str = "farm-morning", **extra: Any) -> dict[str, Any]:
    return {
        "prompt_key": key,
        "prompt_type": "situation",
        "text": "Describe a morning in the fields.",
        "text_language_tag": "en",
        "source_and_licence": "written by the team, CC BY 4.0",
        "topic_tags": ["farming"],
        **extra,
    }


def _create(
    client: TestClient,
    body: dict[str, Any],
    image: bytes | None = None,
    audio: bytes | None = None,
) -> Any:
    files = {}
    if image is not None:
        files["image"] = ("picture.png", image, "image/png")
    if audio is not None:
        files["audio"] = ("spoken.ogg", audio, "audio/ogg")
    return client.post(ADMIN, data={"prompt": json.dumps(body)}, files=files or None)


@pytest.fixture
def admin(client: TestClient, make_user: MakeUser) -> TestUser:
    user = make_user("admin", "admin")
    act_as(client, user)
    return user


def _approved(client: TestClient, body: dict[str, Any], **files: bytes) -> dict[str, Any]:
    created = _create(client, body, **files)
    assert created.status_code == 201, created.text
    approved = client.post(f"{ADMIN}/{created.json()['id']}/approve")
    assert approved.status_code == 200, approved.text
    result: dict[str, Any] = approved.json()
    return result


def _media_files(tmp_path: Path) -> list[Path]:
    return [p for p in (tmp_path / "objects" / "test-derived").rglob("*") if p.is_file()]


# ------------------------------------------------------------------ library management


def test_new_prompts_are_drafts_and_creation_is_audited(
    client: TestClient, admin: TestUser, db: Session
) -> None:
    response = _create(client, _situation())
    assert response.status_code == 201, response.text
    prompt = response.json()
    assert (prompt["status"], prompt["version"], prompt["has_image"]) == ("draft", 1, False)
    assert db.scalar(select(AuditEvent.action).order_by(AuditEvent.occurred_at.desc())) == (
        "prompt.create"
    )
    again = _create(client, _situation())
    assert again.json()["code"] == "prompt_key_taken"


def test_each_prompt_type_needs_its_content(client: TestClient, admin: TestUser) -> None:
    assert _create(client, _situation(text=None)).status_code == 422
    read = _situation("read-one", prompt_type="read_sentence", script_code=None)
    assert _create(client, read).status_code == 422
    image = _situation("img-one", prompt_type="image", text=None)
    assert _create(client, image).json()["code"] == "image_mismatch"
    assert _create(client, _situation("sit-two"), image=FAKE_PNG).json()["code"] == (
        "image_mismatch"
    )
    created = _create(client, image, image=FAKE_PNG)
    assert created.status_code == 201, created.text
    assert created.json()["has_image"] is True


def test_media_must_be_a_supported_format(
    client: TestClient, admin: TestUser, tmp_path: Path
) -> None:
    image = _situation("img-svg", prompt_type="image", text=None)
    svg = _create(client, image, image=b'<svg xmlns="http://www.w3.org/2000/svg"></svg>')
    assert svg.json()["code"] == "image_unsupported"
    bad_audio = _create(client, _situation(), audio=b"not audio at all")
    assert bad_audio.json()["code"] == "audio_unsupported"
    assert _media_files(tmp_path) == []


def test_oversized_media_is_refused_and_not_kept(
    client: TestClient, admin: TestUser, tmp_path: Path, settings: Any
) -> None:
    settings.prompt_image_max_bytes = 16
    image = _situation("img-big", prompt_type="image", text=None)
    assert _create(client, image, image=FAKE_PNG).status_code == 413
    assert _media_files(tmp_path) == []


def test_only_staff_manage_the_library_and_only_admins_approve(
    client: TestClient, make_user: MakeUser
) -> None:
    act_as(client, make_user("asha", "contributor"))
    assert _create(client, _situation()).status_code == 403
    assert client.get(ADMIN).status_code == 403

    act_as(client, make_user("rita", "reviewer"))
    draft = _create(client, _situation())
    assert draft.status_code == 201
    assert client.post(f"{ADMIN}/{draft.json()['id']}/approve").status_code == 403
    assert [p["prompt_key"] for p in client.get(ADMIN).json()["items"]] == ["farm-morning"]


def test_editing_creates_a_new_draft_version(
    client: TestClient, admin: TestUser, db: Session
) -> None:
    first = _approved(client, _situation())
    edited = client.post(
        f"{ADMIN}/{first['id']}/versions",
        data={"prompt": json.dumps({"text": "Describe an evening in the fields."})},
    )
    assert edited.status_code == 201, edited.text
    second = edited.json()
    assert (second["version"], second["status"]) == (2, "draft")
    assert second["topic_tags"] == ["farming"]  # copied from version 1
    original = db.get(Prompt, uuid.UUID(first["id"]))
    assert original is not None and original.text == "Describe a morning in the fields."

    approved = client.post(f"{ADMIN}/{second['id']}/approve").json()
    assert approved["status"] == "approved"
    statuses = client.get(ADMIN, params={"status": "retired"}).json()["items"]
    assert [p["id"] for p in statuses] == [first["id"]]


def test_a_version_cannot_drop_required_content(client: TestClient, admin: TestUser) -> None:
    read = _approved(
        client, _situation("read-one", prompt_type="read_sentence", script_code="Latn")
    )
    response = client.post(
        f"{ADMIN}/{read['id']}/versions", data={"prompt": json.dumps({"script_code": None})}
    )
    assert response.json()["code"] == "prompt_invalid"


def test_approval_and_retirement_rules(client: TestClient, admin: TestUser) -> None:
    prompt = _approved(client, _situation())
    assert client.post(f"{ADMIN}/{prompt['id']}/approve").json()["code"] == "prompt_not_draft"
    assert client.post(f"{ADMIN}/{prompt['id']}/retire").json()["status"] == "retired"
    assert client.post(f"{ADMIN}/{prompt['id']}/retire").json()["code"] == "prompt_retired"
    draft = _create(client, _situation("other-key")).json()
    assert client.post(f"{ADMIN}/{draft['id']}/retire").json()["status"] == "retired"
