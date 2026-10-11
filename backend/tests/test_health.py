import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine

from app.db import get_engine
from app.main import create_app
from app.object_store import Bucket, LocalObjectStore, get_object_store


@pytest.fixture
def app_and_client(tmp_path: Path) -> Iterator[tuple[object, TestClient]]:
    app = create_app()
    store = LocalObjectStore(tmp_path, {b: b.value for b in Bucket}, "http://test", "secret")
    app.dependency_overrides[get_object_store] = lambda: store
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
    assert response.json()["storage"] == "ok"


def test_readyz_ok_when_database_answers(app_and_client: tuple[object, TestClient]) -> None:
    app, client = app_and_client
    sqlite_in_memory = create_engine("sqlite://")
    app.dependency_overrides[get_engine] = lambda: sqlite_in_memory  # type: ignore[attr-defined]
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "storage": "ok"}


def test_readyz_reports_unreachable_storage(
    app_and_client: tuple[object, TestClient], tmp_path: Path
) -> None:
    app, client = app_and_client
    store = LocalObjectStore(tmp_path / "s", {b: b.value for b in Bucket}, "http://test", "k")
    shutil.rmtree(tmp_path / "s" / "originals")  # bucket gone
    app.dependency_overrides[get_engine] = lambda: create_engine("sqlite://")  # type: ignore[attr-defined]
    app.dependency_overrides[get_object_store] = lambda: store  # type: ignore[attr-defined]
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["storage"] == "unreachable"
