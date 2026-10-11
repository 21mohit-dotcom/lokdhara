import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.db import DbSession
from app.modules.identity.deps import AdminUser, Context
from app.modules.processing import service
from app.modules.processing.schemas import JobListOut, JobOut

router = APIRouter(tags=["jobs"])


@router.get("/admin/jobs")
def list_jobs(
    _admin: AdminUser,
    db: DbSession,
    status: Literal["queued", "running", "succeeded", "failed"] = "failed",
    limit: Annotated[int, Query(gt=0, le=200)] = 50,
) -> JobListOut:
    jobs = service.list_jobs(db, status, limit)
    return JobListOut(items=[JobOut.model_validate(j, from_attributes=True) for j in jobs])


@router.post("/admin/jobs/{job_id}/retry")
def retry_job(job_id: uuid.UUID, admin: AdminUser, db: DbSession, context: Context) -> JobOut:
    job = service.retry_job(db, actor=admin, job_id=job_id, context=context)
    return JobOut.model_validate(job, from_attributes=True)
