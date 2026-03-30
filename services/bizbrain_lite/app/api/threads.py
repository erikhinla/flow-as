from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_api_token
from app.schemas.thread import ThreadCreate, ThreadRecord, ThreadUpdate
from app.services.registry_service import registry_service

router = APIRouter(prefix="/threads", tags=["threads"], dependencies=[Depends(require_api_token)])


@router.post("", response_model=ThreadRecord)
async def create_thread(payload: ThreadCreate) -> ThreadRecord:
    return await registry_service.create_thread(payload)


@router.get("/{thread_id}", response_model=ThreadRecord)
async def get_thread(thread_id: str) -> ThreadRecord:
    thread = await registry_service.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return thread


@router.patch("/{thread_id}", response_model=ThreadRecord)
async def update_thread(thread_id: str, payload: ThreadUpdate) -> ThreadRecord:
    thread = await registry_service.update_thread(thread_id, payload)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return thread

