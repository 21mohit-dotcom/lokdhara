"""Shared steps for the submission and upload tests. All data is synthetic."""

import uuid
from typing import Any

from fastapi.testclient import TestClient

SUBMISSIONS = "/api/v1/submissions"


def own_speaker(client: TestClient) -> str:
    response = client.post("/api/v1/speakers", json={"for_self": True})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def draft_body(speaker_id: str, **fields: Any) -> dict[str, Any]:
    return {
        "client_submission_id": str(uuid.uuid4()),
        "speaker_id": speaker_id,
        "kind": "audio",
        "content_type": "story",
        "collection_method": "self_recorded",
        "recording_mode": "free",
        **fields,
    }


def create_draft(client: TestClient, speaker_id: str, **fields: Any) -> dict[str, Any]:
    response = client.post(SUBMISSIONS, json=draft_body(speaker_id, **fields))
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result
