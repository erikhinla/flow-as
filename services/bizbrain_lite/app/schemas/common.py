from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SourceEnum(str, Enum):
    OPENCLAW = "openclaw"
    ALPHA = "alpha"
    BETA = "beta"
    GAMMA = "gamma"
    HUB = "hub"


class RiskLevelEnum(str, Enum):
    ALPHA = "alpha"
    BETA = "beta"
    GAMMA = "gamma"


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStateEnum(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    BLOCKED = "blocked"
    ERROR = "error"


class ThreadStateEnum(str, Enum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    CLOSED = "closed"


class BaseRecord(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    metadata: dict[str, Any] = Field(default_factory=dict)

