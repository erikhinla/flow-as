from typing import Any

from pydantic import BaseModel, Field

from .common import AgentStateEnum, BaseRecord, now_utc


class AgentStatusRecord(BaseRecord):
    agent_id: str
    state: AgentStateEnum = AgentStateEnum.IDLE
    current_task_id: str | None = None
    heartbeat_at: str = Field(default_factory=lambda: now_utc().isoformat())
    queue_depth: int = 0
    last_error: str | None = None
    capabilities: list[str] = Field(default_factory=list)


class AgentStatusUpdate(BaseModel):
    state: AgentStateEnum
    current_task_id: str | None = None
    queue_depth: int | None = None
    last_error: str | None = None
    capabilities: list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentHeartbeat(BaseModel):
    current_task_id: str | None = None
    queue_depth: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

