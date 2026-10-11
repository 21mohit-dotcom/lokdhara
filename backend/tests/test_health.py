from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine

from app.db import get_engine
from app.main import create_app


@pytest.fixture
def app_and_client() -> Iterator[tuple[object, TestClient]]:
    app = create_app()
    with TestClient(app) as client:
        yield app, client


def test_healthz_is_ok_without_dependencies(app_and_client: tuple[object, TestClient]) -> None:
    _, client = app_and_client
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_reports_unreachable_database(app_and_client: tuple[object, TestClient]) -> None:
    app, client = app_and_client
    # Port 1 refuses connections immediately.
    unreachable: Engine = create_engine(
        "postgresql+psycopg://nobody:nothing@127.0.0.1:1/none", connect_args={"connect_timeout": 1}
    )
    app.dependency_overrides[get_engine] = lambda: unreachable  # type: ignore[attr-defined]
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["database"] == "unreachable"


def test_readyz_ok_when_database_answers(app_and_client: tuple[object, TestClient]) -> None:
    app, client = app_and_client
    sqlite_in_memory = create_engine("sqlite://")
    app.dependency_overrides[get_engine] = lambda: sqlite_in_memory  # type: ignore[attr-defined]
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
