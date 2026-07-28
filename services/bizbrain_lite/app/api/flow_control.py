from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_api_token
from app.config.database import get_db_session
from app.models.flow_job_record import JobRecord
from app.services.flow_filesystem_control import (
    FlowControlError,
    approve_task,
    block_task,
    get_task,
    get_state_root,
    list_tasks,
    runtime_status,
    submit_task,
)


router = APIRouter(tags=["flow-control"], prefix="/flow", dependencies=[Depends(require_api_token)])


class SubmitRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    goal: str = Field(..., min_length=10, max_length=2000)
    risk_tier: str
    owner_role: str | None = None
    source: str = "landing_page"
    task_type: str = Field(default="internal_review", min_length=3, max_length=100)
    inputs: dict[str, Any] = Field(default_factory=dict)
    output_required: str = "Artifact written to ~/.openclaw/state/artifacts/{task_id}/"


class ApprovalRequest(BaseModel):
    task_id: str
    actor: str = "landing_page"


class BlockRequest(BaseModel):
    task_id: str
    reason: str = Field(..., min_length=3, max_length=500)
    actor: str = "landing_page"


def _handle_flow_error(exc: FlowControlError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _model_job_payload(job: JobRecord) -> dict[str, Any]:
    """Return dashboard-safe model job state without exposing provider secrets."""
    return {
        "task_id": job.task_id,
        "title": job.title,
        "goal": job.goal,
        "task_type": job.task_type,
        "risk_tier": job.risk_tier,
        "owner_role": job.owner,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "artifact_path": job.result_pointer,
        "error_message": job.error_message,
    }


@router.get("/status")
async def flow_status() -> dict[str, Any]:
    return runtime_status()


@router.get("/model/jobs")
async def model_jobs(db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    """List provider-backed jobs submitted from the dashboard."""
    result = await db.execute(
        select(JobRecord)
        .where(JobRecord.source == "dashboard")
        .order_by(JobRecord.created_at.desc())
        .limit(100)
    )
    return {"tasks": [_model_job_payload(job) for job in result.scalars().all()]}


@router.get("/model/jobs/{task_id}")
async def model_job(task_id: str, db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    result = await db.execute(select(JobRecord).where(JobRecord.job_id == task_id))
    job = result.scalar_one_or_none()
    if not job or job.source != "dashboard":
        raise HTTPException(status_code=404, detail="Model task not found")
    return _model_job_payload(job)


@router.get("/model/jobs/{task_id}/artifact")
async def model_job_artifact(task_id: str, db: AsyncSession = Depends(get_db_session)) -> dict[str, str]:
    result = await db.execute(select(JobRecord).where(JobRecord.job_id == task_id))
    job = result.scalar_one_or_none()
    if not job or job.source != "dashboard":
        raise HTTPException(status_code=404, detail="Model task not found")
    if not job.result_pointer:
        raise HTTPException(status_code=404, detail="No output is available for this task yet")

    artifact_path = Path(job.result_pointer).resolve()
    allowed_root = Path("/app/runtime/reviews").resolve()
    if not artifact_path.is_relative_to(allowed_root):
        raise HTTPException(status_code=403, detail="Artifact path is outside the model artifact store")
    if not artifact_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file is unavailable")
    return {"path": str(artifact_path), "content": artifact_path.read_text(encoding="utf-8")[:1_000_000]}


@router.get("/tasks")
async def flow_tasks(queue: str | None = None) -> dict[str, Any]:
    try:
        return {"tasks": list_tasks(queue=queue)}
    except FlowControlError as exc:
        raise _handle_flow_error(exc)


@router.get("/tasks/{task_id}")
async def flow_task(task_id: str) -> dict[str, Any]:
    try:
        return get_task(task_id)
    except FlowControlError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/submit")
async def flow_submit(request: SubmitRequest) -> dict[str, Any]:
    try:
        task = submit_task(request.model_dump(), actor=request.source)
        return {"status": "accepted", "task": task}
    except FlowControlError as exc:
        raise _handle_flow_error(exc)


@router.get("/tasks/{task_id}/artifact")
async def flow_task_artifact(task_id: str) -> dict[str, str]:
    try:
        task = get_task(task_id)
    except FlowControlError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    raw_path = task.get("artifact_path")
    if not raw_path:
        raise HTTPException(status_code=404, detail="No artifact is available for this task")

    artifact_path = Path(raw_path).resolve()
    allowed_roots = (
        (get_state_root() / "artifacts").resolve(),
        Path("/app/runtime/reviews").resolve(),
    )
    if not any(artifact_path.is_relative_to(root) for root in allowed_roots):
        raise HTTPException(status_code=403, detail="Artifact path is outside the FLOW artifact store")
    if not artifact_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file is unavailable")

    return {
        "path": str(artifact_path),
        "content": artifact_path.read_text(encoding="utf-8")[:1_000_000],
    }


@router.post("/approve")
async def flow_approve(request: ApprovalRequest) -> dict[str, Any]:
    try:
        return {"status": "approved", "task": approve_task(request.task_id, actor=request.actor)}
    except FlowControlError as exc:
        raise _handle_flow_error(exc)


@router.post("/block")
async def flow_block(request: BlockRequest) -> dict[str, Any]:
    try:
        return {"status": "blocked", "task": block_task(request.task_id, request.reason, actor=request.actor)}
    except FlowControlError as exc:
        raise _handle_flow_error(exc)
