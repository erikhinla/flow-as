from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from .common import BaseRecord, RiskLevelEnum, now_utc
from app.services.input_normalization import normalize_text, normalize_value


class ThreadHandoffRecord(BaseRecord):
    handoff_id: str = Field(default_factory=lambda: f"handoff_{uuid4().hex}")
    thread_id: str
    from_agent: str
    to_agent: str
    reason: str
    context_summary: str
    risk_level: RiskLevelEnum = RiskLevelEnum.BETA
    acknowledged_at: str | None = None


class HandoffCreate(BaseModel):
    thread_id: str
    from_agent: str
    to_agent: str
    reason: str
    context_summary: str
    risk_level: RiskLevelEnum = RiskLevelEnum.BETA
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("reason", "context_summary", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: str) -> str:
        return normalize_text(value)

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return normalize_value(value)


class HandoffAck(BaseModel):
    acknowledged_by: str
    acknowledged_at: str = Field(default_factory=lambda: now_utc().isoformat())

    @field_validator("acknowledged_by", mode="before")
    @classmethod
    def normalize_acknowledged_by(cls, value: str) -> str:
        return normalize_text(value)

