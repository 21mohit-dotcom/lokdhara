"""Liveness and readiness endpoints (docs/API_SPECIFICATION.md §9)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import Engine

from app.db import database_is_reachable, get_engine
from app.object_store import ObjectStore, get_object_store

router = APIRouter(tags=["ops"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """The process is up. Does not touch dependencies."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz(
    response: Response,
    engine: Annotated[Engine, Depends(get_engine)],
    store: Annotated[ObjectStore, Depends(get_object_store)],
) -> dict[str, str]:
    """The process can serve traffic: the database and object storage answer."""
    checks = {
        "database": "ok" if database_is_reachable(engine) else "unreachable",
        "storage": "ok" if store.is_reachable() else "unreachable",
    }
    if "unreachable" in checks.values():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", **checks}
    return {"status": "ok", **checks}
