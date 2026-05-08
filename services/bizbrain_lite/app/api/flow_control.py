from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import require_api_token
from app.services.flow_filesystem_control import (
    FlowControlError,
    approve_task,
    block_task,
    get_task,
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


@router.get("/status")
async def flow_status() -> dict[str, Any]:
    return runtime_status()


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
