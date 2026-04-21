from typing import Any

from pydantic import BaseModel, Field, field_validator

from .common import AgentStateEnum, BaseRecord, now_utc
from app.services.input_normalization import normalize_text, normalize_value


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

    @field_validator("last_error", mode="before")
    @classmethod
    def normalize_last_error(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_text(value)

    @field_validator("capabilities", mode="before")
    @classmethod
    def normalize_capabilities(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [normalize_text(item) for item in value]

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return normalize_value(value)


class AgentHeartbeat(BaseModel):
    current_task_id: str | None = None
    queue_depth: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return normalize_value(value)

