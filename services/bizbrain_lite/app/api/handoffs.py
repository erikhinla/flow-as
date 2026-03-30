from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_api_token
from app.schemas.handoff import HandoffAck, HandoffCreate, ThreadHandoffRecord
from app.services.registry_service import registry_service

router = APIRouter(prefix="/handoffs", tags=["handoffs"], dependencies=[Depends(require_api_token)])


@router.post("", response_model=ThreadHandoffRecord)
async def create_handoff(payload: HandoffCreate) -> ThreadHandoffRecord:
    return await registry_service.create_handoff(payload)


@router.get("", response_model=list[ThreadHandoffRecord])
async def list_handoffs() -> list[ThreadHandoffRecord]:
    return await registry_service.list_handoffs()


@router.post("/{handoff_id}/ack", response_model=ThreadHandoffRecord)
async def ack_handoff(handoff_id: str, payload: HandoffAck) -> ThreadHandoffRecord:
    handoff = await registry_service.ack_handoff(handoff_id, payload)
    if not handoff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Handoff not found")
    return handoff

