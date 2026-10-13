"""The worker's text check: exact duplicate text and script mismatches (docs/
TEXT_PROCESSING_PIPELINE.md §5, §10).

Sample text is synthetic Hindi or English, never collected community text.
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, literal, select
from sqlalchemy.orm import Session

from app.modules.processing import queue
from app.modules.processing.models import ProcessingRun
from app.modules.submissions.models import RelatedItem
from app.modules.submissions.text_processing import sql_search_key
from app.text import normalize
from tests.conftest import MakeUser, act_as, requires_postgres
from tests.submission_helpers import SUBMISSIONS, create_draft, give_consent, own_speaker

pytestmark = requires_postgres

SENTENCE = "यह एक परीक्षण वाक्य है।"


@pytest.fixture
def speaker_id(client: TestClient, make_user: MakeUser, db: Session) -> str:
    act_as(client, make_user("asha", "contributor"))
    speaker = own_speaker(client)
    give_consent(client, db, speaker)
    return speaker


def text_draft(client: TestClient, speaker_id: str, content: str, **fields: Any) -> str:
    """A text submission with one standalone layer; returns the submission ID."""
    draft = str(create_draft(client, speaker_id, kind="text", recording_mode=None)["id"])
    body = {
        "layer_type": "standalone",
        "entry_type": "sentence",
        "language_tag": "unr",
        "script_code": "Deva",
        "content": content,
        **fields,
    }
    response = client.post(f"{SUBMISSIONS}/{draft}/text-layers", json=body)
    assert response.status_code == 201, response.text
    return draft


def submit(client: TestClient, submission_id: str) -> uuid.UUID:
    assert client.post(f"{SUBMISSIONS}/{submission_id}/submit").status_code == 200
    return uuid.UUID(submission_id)


def run_jobs(engine: Engine) -> None:
    while queue.process_one(engine, "test-worker", 60):
        pass


def related(db: Session) -> list[tuple[uuid.UUID, uuid.UUID, str]]:
    return [
        (item.submission_a, item.submission_b, item.relation)
        for item in db.scalars(select(RelatedItem))
    ]


@pytest.mark.parametrize(
    "text", [SENTENCE, "  a\t\u00a0 b  ", "line one \n  line two\n", "क्‍ष  \t", " \u00a0 "]
)
def test_the_database_computes_the_same_search_key(db: Session, text: str) -> None:
    assert db.scalar(select(sql_search_key(literal(text)))) == normalize.search_key(text)


def test_the_same_text_differently_spaced_is_linked(
    client: TestClient, speaker_id: str, engine: Engine, db: Session
) -> None:
    first = submit(client, text_draft(client, speaker_id, SENTENCE))
    run_jobs(engine)
    second = submit(client, text_draft(client, speaker_id, f"  {SENTENCE.replace(' ', '  ')}"))
    other_language = submit(client, text_draft(client, speaker_id, SENTENCE, language_tag="hi"))
    text_draft(client, speaker_id, SENTENCE)  # never submitted
    run_jobs(engine)

    pair = sorted([first, second])
    assert related(db) == [(pair[0], pair[1], "possible_duplicate")]
    assert other_language not in {*pair}


def test_matching_translations_are_not_duplicates(
    client: TestClient, speaker_id: str, engine: Engine, db: Session
) -> None:
    for content in ("पहला वाक्य", "दूसरा वाक्य"):
        draft = text_draft(client, speaker_id, content)
        source = client.get(f"{SUBMISSIONS}/{draft}").json()["text_layers"][0]["id"]
        translation = {
            "layer_type": "translation",
            "source_layer_id": source,
            "language_tag": "en",
            "script_code": "Latn",
            "content": "A sentence.",
        }
        assert (
            client.post(f"{SUBMISSIONS}/{draft}/text-layers", json=translation).status_code == 201
        )
        submit(client, draft)
    run_jobs(engine)
    assert related(db) == []


def test_checking_again_links_nothing_new_and_counts_mismatches(
    client: TestClient, speaker_id: str, engine: Engine, db: Session
) -> None:
    submit(client, text_draft(client, speaker_id, "Johar"))
    second = submit(client, text_draft(client, speaker_id, "Johar"))
    run_jobs(engine)
    queue.enqueue(db, "text.derive", target_type="submission", target_id=second)
    db.commit()
    run_jobs(engine)

    assert len(related(db)) == 1
    runs = db.scalars(
        select(ProcessingRun).where(ProcessingRun.target_id == second).order_by(ProcessingRun.id)
    ).all()
    assert [run.output_summary for run in runs] == [
        {"layers": 1, "script_mismatch": 1, "duplicates": 1}
    ] * 2
