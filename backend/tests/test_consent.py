"""Consent forms and capture (docs/CONSENT_AND_DATA_GOVERNANCE.md §3, docs/USER_FLOWS.md F2)."""

import base64
import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import ApiError
from app.modules.consents import service
from tests.conftest import MakeUser, act_as, requires_postgres

pytestmark = requires_postgres


@pytest.fixture
def form_id(db: Session) -> str:
    service.ensure_dev_forms(db)
    db.commit()
    form = service.current_form(db, Settings(_env_file=None, env="test"), "hi")
    return str(form.id)


# ------------------------------------------------------------------ forms


def test_current_form_is_the_test_form_with_its_hash(
    client: TestClient, make_user: MakeUser, form_id: str
) -> None:
    act_as(client, make_user("asha", "contributor"))
    response = client.get("/api/v1/consent-forms/current", params={"language": "hi"})
    assert response.status_code == 200
    form = response.json()
    assert form["id"] == form_id
    assert form["is_test_form"] is True
    assert form["text_sha256"] == hashlib.sha256(form["body_markdown"].encode()).hexdigest()
    missing = client.get("/api/v1/consent-forms/current", params={"language": "unr-Deva"})
    assert missing.json()["code"] == "consent_form_not_found"


def test_production_never_offers_test_forms(db: Session, form_id: str) -> None:
    production = Settings(
        _env_file=None,
        env="production",
        secret_key="x" * 40,
        identity_encryption_key=base64.b64encode(bytes(32)).decode(),
    )
    with pytest.raises(ApiError, match="consent_form_not_found"):
        service.current_form(db, production, "hi")
