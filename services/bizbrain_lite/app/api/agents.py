from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_api_token
from app.schemas.agent_status import AgentHeartbeat, AgentStatusRecord, AgentStatusUpdate
from app.services.registry_service import registry_service

router = APIRouter(prefix="/agents", tags=["agents"], dependencies=[Depends(require_api_token)])


@router.post("/{agent_id}/heartbeat", response_model=AgentStatusRecord)
async def heartbeat(agent_id: str, payload: AgentHeartbeat) -> AgentStatusRecord:
    return await registry_service.heartbeat_agent(agent_id, payload)


@router.get("", response_model=list[AgentStatusRecord])
async def list_agents() -> list[AgentStatusRecord]:
    return await registry_service.list_agents()


@router.get("/{agent_id}", response_model=AgentStatusRecord)
async def get_agent(agent_id: str) -> AgentStatusRecord:
    agent = await registry_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.patch("/{agent_id}/status", response_model=AgentStatusRecord)
async def update_status(agent_id: str, payload: AgentStatusUpdate) -> AgentStatusRecord:
    return await registry_service.update_agent_status(agent_id, payload)

