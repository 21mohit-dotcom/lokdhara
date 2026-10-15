"""Comparing two versions of a text (docs/API_SPECIFICATION.md §6).

Sample text is synthetic Hindi or English, never collected community text.
"""

import random
from typing import Any

from fastapi.testclient import TestClient

from app.text.diff import Op, diff
from tests.conftest import MakeUser, act_as, requires_postgres
from tests.submission_helpers import SUBMISSIONS, create_draft, give_consent, own_speaker


def _side(parts: list[tuple[Op, str]], keep: Op) -> str:
    return "".join(text for op, text in parts if op in ("equal", keep))


def test_a_diff_rebuilds_both_versions() -> None:
    letters = "abc कखगािीु्ं \n।"
    rng = random.Random(7)  # noqa: S311 - repeatable test data, not secrets
    for _ in range(500):
        old = "".join(rng.choices(letters, k=rng.randint(0, 20)))
        new = "".join(rng.choices(letters, k=rng.randint(0, 20)))
        parts = diff(old, new)
        assert _side(parts, "delete") == old
        assert _side(parts, "insert") == new
        assert all(text for _, text in parts)


def test_vowel_signs_stay_with_their_consonant() -> None:
    # कि and का differ only in the vowel sign; the diff swaps whole letters.
    assert diff("किताब", "काताब") == [("delete", "कि"), ("insert", "का"), ("equal", "ताब")]


def test_unchanged_text_is_one_equal_part() -> None:
    assert diff("same text", "same text") == [("equal", "same text")]
    assert diff("", "") == []


# ------------------------------------------------------------------ endpoint


def _layer(client: TestClient, submission: str, content: str) -> dict[str, Any]:
    body = {
        "layer_type": "standalone",
        "entry_type": "sentence",
        "language_tag": "en",
        "script_code": "Latn",
        "content": content,
    }
    response = client.post(f"{SUBMISSIONS}/{submission}/text-layers", json=body)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def _revise(client: TestClient, layer: dict[str, Any], content: str) -> dict[str, Any]:
    body = {"base_revision_id": layer["current_revision"]["id"], "content": content}
    response = client.post(f"/api/v1/text-layers/{layer['id']}/revisions", json=body)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def _diff(client: TestClient, a: str, b: str) -> Any:
    return client.get(f"/api/v1/text-revisions/{a}/diff/{b}")


@requires_postgres
def test_two_versions_of_a_text_can_be_compared(
    client: TestClient, make_user: MakeUser, db: Any
) -> None:
    act_as(client, make_user("asha", "contributor"))
    speaker = own_speaker(client)
    give_consent(client, db, speaker)
    draft = str(create_draft(client, speaker, kind="text", recording_mode=None)["id"])
    first = _layer(client, draft, "The river is wide.")
    second = _revise(client, first, "The river is very wide.")
    old, new = first["current_revision"]["id"], second["current_revision"]["id"]

    response = _diff(client, old, new)
    assert response.status_code == 200
    assert response.json()["parts"] == [
        {"op": "equal", "text": "The river is "},
        {"op": "insert", "text": "very "},
        {"op": "equal", "text": "wide."},
    ]

    other = _layer(client, draft, "Another sentence.")["current_revision"]["id"]
    assert _diff(client, old, other).json()["code"] == "different_layers"

    act_as(client, make_user("ravi", "contributor"))
    assert _diff(client, old, new).status_code == 404


@requires_postgres
def test_unknown_versions_are_not_found(client: TestClient, make_user: MakeUser) -> None:
    act_as(client, make_user("asha", "contributor"))
    missing = "01890000-0000-7000-8000-000000000000"
    response = _diff(client, missing, missing)
    assert response.json()["code"] == "text_revision_not_found"
