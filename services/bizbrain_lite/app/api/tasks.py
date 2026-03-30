from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_api_token
from app.schemas.task import TaskCreate, TaskEvent, TaskRecord, TaskUpdate
from app.services.registry_service import registry_service

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(require_api_token)])


@router.post("", response_model=TaskRecord)
async def create_task(payload: TaskCreate) -> TaskRecord:
    return await registry_service.create_task(payload)


@router.get("", response_model=list[TaskRecord])
async def list_tasks() -> list[TaskRecord]:
    return await registry_service.list_tasks()


@router.get("/{task_id}", response_model=TaskRecord)
async def get_task(task_id: str) -> TaskRecord:
    task = await registry_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskRecord)
async def update_task(task_id: str, payload: TaskUpdate) -> TaskRecord:
    task = await registry_service.update_task(task_id, payload)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("/{task_id}/events")
async def append_task_event(task_id: str, payload: TaskEvent) -> dict[str, str]:
    await registry_service.add_task_event(task_id, payload)
    return {"status": "ok"}


@router.get("/{task_id}/events")
async def list_task_events(task_id: str) -> dict[str, object]:
    return {"task_id": task_id, "events": await registry_service.get_task_events(task_id)}


@router.get("/{task_id}/artifacts")
async def list_task_artifacts(task_id: str) -> dict[str, object]:
    return {"task_id": task_id, "artifacts": await registry_service.list_task_artifacts(task_id)}

