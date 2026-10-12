"""Prompt library (docs/API_SPECIFICATION.md §4a)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, UploadFile, status

from app.db import DbSession
from app.forms import parse_json_field
from app.modules.identity.deps import Context, SettingsDep, require_roles
from app.modules.identity.service import AuthenticatedUser
from app.modules.prompts import service
from app.modules.prompts.models import Prompt
from app.modules.prompts.schemas import (
    PromptCreateRequest,
    PromptListOut,
    PromptOut,
    PromptStatus,
    PromptType,
    PromptVersionRequest,
)
from app.object_store import ObjectStore, get_object_store

router = APIRouter(tags=["prompts"])

Staff = Annotated[AuthenticatedUser, Depends(require_roles(*service.STAFF_ROLES))]
Admin = Annotated[AuthenticatedUser, Depends(require_roles("admin"))]
Store = Annotated[ObjectStore, Depends(get_object_store)]


def _library_out(prompt: Prompt) -> PromptOut:
    media = {"has_image", "has_audio"}
    fields = {f: getattr(prompt, f) for f in PromptOut.model_fields if f not in media}
    return PromptOut(
        **fields,
        has_image=prompt.image_object_key is not None,
        has_audio=prompt.prompt_audio_object_key is not None,
    )


@router.get("/admin/prompts")
def list_prompts(
    _staff: Staff,
    db: DbSession,
    status: PromptStatus | None = None,
    prompt_type: Annotated[PromptType | None, Query(alias="type")] = None,
    limit: Annotated[int, Query(gt=0, le=500)] = 200,
) -> PromptListOut:
    found = service.list_prompts(db, status=status, prompt_type=prompt_type, limit=limit)
    return PromptListOut(items=[_library_out(p) for p in found])


@router.post("/admin/prompts", status_code=status.HTTP_201_CREATED)
def create_prompt(
    prompt: Annotated[str, Form(description="PromptCreateRequest as JSON")],
    staff: Staff,
    db: DbSession,
    settings: SettingsDep,
    store: Store,
    context: Context,
    image: UploadFile | None = None,
    audio: UploadFile | None = None,
) -> PromptOut:
    """Multipart: the prompt as JSON in `prompt`, plus `image` (image prompts) and an optional
    spoken version in `audio`. New prompts start as drafts."""
    created = service.create_prompt(
        db,
        store,
        settings,
        actor=staff,
        body=parse_json_field(PromptCreateRequest, prompt, "prompt"),
        image=image.file if image else None,
        audio=audio.file if audio else None,
        context=context,
    )
    return _library_out(created)


@router.post("/admin/prompts/{prompt_id}/versions", status_code=status.HTTP_201_CREATED)
def new_version(
    prompt_id: uuid.UUID,
    prompt: Annotated[str, Form(description="PromptVersionRequest as JSON")],
    staff: Staff,
    db: DbSession,
    settings: SettingsDep,
    store: Store,
    context: Context,
    image: UploadFile | None = None,
    audio: UploadFile | None = None,
) -> PromptOut:
    """Editing a prompt creates a new draft version; recordings keep the version they used."""
    created = service.new_version(
        db,
        store,
        settings,
        actor=staff,
        prompt_id=prompt_id,
        body=parse_json_field(PromptVersionRequest, prompt, "prompt"),
        image=image.file if image else None,
        audio=audio.file if audio else None,
        context=context,
    )
    return _library_out(created)


@router.post("/admin/prompts/{prompt_id}/approve")
def approve(prompt_id: uuid.UUID, admin: Admin, db: DbSession, context: Context) -> PromptOut:
    return _library_out(service.approve(db, actor=admin, prompt_id=prompt_id, context=context))


@router.post("/admin/prompts/{prompt_id}/retire")
def retire(prompt_id: uuid.UUID, admin: Admin, db: DbSession, context: Context) -> PromptOut:
    return _library_out(service.retire(db, actor=admin, prompt_id=prompt_id, context=context))
