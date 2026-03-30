from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .common import BaseRecord, RiskLevelEnum, now_utc


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


class HandoffAck(BaseModel):
    acknowledged_by: str
    acknowledged_at: str = Field(default_factory=lambda: now_utc().isoformat())

