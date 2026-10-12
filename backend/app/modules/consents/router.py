"""Consent forms and consent records (docs/API_SPECIFICATION.md §3)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.db import DbSession
from app.modules.consents import service
from app.modules.consents.schemas import ConsentFormOut
from app.modules.identity.deps import CurrentUser, SettingsDep

router = APIRouter(tags=["consent"])


@router.get("/consent-forms/current")
def current_form(
    _user: CurrentUser,
    db: DbSession,
    settings: SettingsDep,
    language: Annotated[str, Query(pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")] = "hi",
) -> ConsentFormOut:
    form = service.current_form(db, settings, language)
    return ConsentFormOut.model_validate(form, from_attributes=True)
