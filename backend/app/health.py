"""Liveness and readiness endpoints (docs/API_SPECIFICATION.md §9)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import Engine

from app.db import database_is_reachable, get_engine

router = APIRouter(tags=["ops"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """The process is up. Does not touch dependencies."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz(response: Response, engine: Annotated[Engine, Depends(get_engine)]) -> dict[str, str]:
    """The process can serve traffic: the database answers."""
    if not database_is_reachable(engine):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}
