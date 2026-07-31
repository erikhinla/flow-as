from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
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
        "task_id": job.job_id,
        "source_task_id": job.task_id,
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
        "output_required": job.output_required,
        "error_message": job.error_message,
    }


def _filesystem_job_payload(task: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy filesystem tasks into the dashboard task contract."""
    return {
        "task_id": task.get("task_id"),
        "source_task_id": task.get("task_id"),
        "title": task.get("title") or "Untitled FLOW task",
        "goal": task.get("goal") or "",
        "task_type": task.get("task_type") or "classification",
        "risk_tier": task.get("risk_tier") or "time_loss",
        "owner_role": task.get("owner_role") or task.get("preferred_owner") or "beta",
        "status": task.get("status") or task.get("queue") or "pending",
        "created_at": task.get("created_at"),
        "updated_at": task.get("updated_at"),
        "completed_at": task.get("completed_at"),
        "artifact_path": task.get("artifact_path"),
        "output_required": task.get("output_required"),
        "error_message": task.get("error_message") or task.get("error"),
    }


@router.get("/status")
async def flow_status() -> dict[str, Any]:
    return runtime_status()


def _is_postgres_model_job(job: JobRecord) -> bool:
    """Jobs the dashboard library can open (not ephemeral healthchecks only)."""
    source = (job.source or "").strip().lower()
    if source in {"dashboard", "manual", "webhook", "landing_page", "discord", "proof"}:
        return True
    # Always include rows that already produced a reviewable artifact
    return bool(job.result_pointer)


def _looks_like_capability_refusal(content: str) -> bool:
    opening = " ".join(content.strip().lower().split())[:1_500]
    markers = (
        "don't have the capability",
        "do not have the capability",
        "beyond the toolset",
        "beyond the tools",
        "blocker summary",
        "i'm sorry, but i don't have",
        "i am sorry, but i don't have",
        "cannot generate the full set",
        "no graphic editors",
        "no video rendering",
        "not supported",
        "goes beyond the toolset",
    )
    return any(marker in opening for marker in markers)


def _artifact_payload(task_id: str, artifact_path: Path) -> dict[str, Any]:
    allowed_root = Path("/app/runtime/reviews").resolve()
    if not artifact_path.is_relative_to(allowed_root):
        raise HTTPException(status_code=403, detail="Artifact path is outside the model artifact store")
    if not artifact_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file is unavailable")
    files_root = (artifact_path.parent / "files").resolve()
    files: list[dict[str, Any]] = []
    if files_root.is_dir():
        for path in sorted(files_root.rglob("*")):
            if path.is_file():
                relative_path = path.relative_to(files_root)
                files.append(
                    {
                        "name": path.name,
                        "relative_path": str(relative_path),
                        "size_bytes": path.stat().st_size,
                        "url": f"/api/flow/model/jobs/{task_id}/files/{relative_path.as_posix()}",
                    }
                )
    content = artifact_path.read_text(encoding="utf-8")[:1_000_000]
    incomplete = _looks_like_capability_refusal(content) and not any(
        f["name"].lower().endswith((".mp4", ".mov", ".png", ".jpg", ".jpeg", ".webp"))
        for f in files
    )
    return {
        "path": str(artifact_path),
        "content": content,
        "files": files,
        "incomplete": incomplete,
        "has_media_files": any(
            f["name"].lower().endswith((".mp4", ".mov", ".png", ".jpg", ".jpeg", ".webp"))
            for f in files
        ),
    }


@router.get("/model/jobs")
async def model_jobs(db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    """List every FLOW job in one dashboard library.

    Includes dashboard submissions and operator/API jobs (manual, webhook, …).
    Previously only source=dashboard was listed, which hid successful media re-runs
    submitted outside the dashboard and left users staring at chat-only refusals.
    """
    result = await db.execute(
        select(JobRecord).order_by(JobRecord.created_at.desc()).limit(150)
    )
    model_tasks = [
        _model_job_payload(job)
        for job in result.scalars().all()
        if _is_postgres_model_job(job)
    ]
    known_ids = {task["task_id"] for task in model_tasks}
    filesystem_tasks = [
        _filesystem_job_payload(task)
        for task in list_tasks()
        if task.get("task_id") not in known_ids
    ]
    tasks = model_tasks + filesystem_tasks
    tasks.sort(
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )
    return {"tasks": tasks[:100]}


@router.get("/model/jobs/{task_id}")
async def model_job(task_id: str, db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    result = await db.execute(select(JobRecord).where(JobRecord.job_id == task_id))
    job = result.scalar_one_or_none()
    if job:
        return _model_job_payload(job)
    try:
        return _filesystem_job_payload(get_task(task_id))
    except FlowControlError:
        raise HTTPException(status_code=404, detail="FLOW task not found")


@router.get("/model/jobs/{task_id}/artifact")
async def model_job_artifact(task_id: str, db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    result = await db.execute(select(JobRecord).where(JobRecord.job_id == task_id))
    job = result.scalar_one_or_none()
    if not job:
        return await flow_task_artifact(task_id)
    if not job.result_pointer:
        raise HTTPException(status_code=404, detail="No output is available for this task yet")

    artifact_path = Path(job.result_pointer).resolve()
    # Map host paths written by workers onto the container review mount
    text_path = str(artifact_path)
    if text_path.startswith("/opt/flow-as/runtime/reviews/"):
        artifact_path = Path(
            text_path.replace("/opt/flow-as/runtime/reviews/", "/app/runtime/reviews/", 1)
        ).resolve()
    return _artifact_payload(task_id, artifact_path)


@router.get("/model/jobs/{task_id}/files/{relative_path:path}")
async def model_job_file(
    task_id: str,
    relative_path: str,
    db: AsyncSession = Depends(get_db_session),
) -> FileResponse:
    result = await db.execute(select(JobRecord).where(JobRecord.job_id == task_id))
    job = result.scalar_one_or_none()
    if not job or not job.result_pointer:
        raise HTTPException(status_code=404, detail="Model task not found")

    pointer = Path(job.result_pointer)
    text_path = str(pointer)
    if text_path.startswith("/opt/flow-as/runtime/reviews/"):
        pointer = Path(
            text_path.replace("/opt/flow-as/runtime/reviews/", "/app/runtime/reviews/", 1)
        )
    files_root = (pointer.resolve().parent / "files").resolve()
    file_path = (files_root / relative_path).resolve()
    if not file_path.is_relative_to(files_root):
        raise HTTPException(status_code=403, detail="Artifact path is outside the task file store")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file is unavailable")
    return FileResponse(file_path, filename=file_path.name)


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
