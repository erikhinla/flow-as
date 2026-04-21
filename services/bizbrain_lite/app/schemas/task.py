from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from .common import BaseRecord, SourceEnum, TaskStatusEnum, now_utc
from app.services.input_normalization import normalize_text, normalize_value


class TaskRecord(BaseRecord):
    task_id: str = Field(default_factory=lambda: f"task_{uuid4().hex}")
    title: str
    source: SourceEnum
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    priority: int = 3
    owner_agent: str | None = None
    thread_id: str | None = None
    repo_path: str | None = None


class TaskCreate(BaseModel):
    title: str
    source: SourceEnum
    priority: int = 3
    owner_agent: str | None = None
    thread_id: str | None = None
    repo_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return normalize_text(value)

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return normalize_value(value)


class TaskUpdate(BaseModel):
    status: TaskStatusEnum | None = None
    priority: int | None = None
    owner_agent: str | None = None
    thread_id: str | None = None
    repo_path: str | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        return normalize_value(value)


class TaskEvent(BaseModel):
    event_type: str
    detail: str
    source: SourceEnum
    metadata: dict[str, Any] = Field(default_factory=dict)
    at: str = Field(default_factory=lambda: now_utc().isoformat())

    @field_validator("detail", mode="before")
    @classmethod
    def normalize_detail(cls, value: str) -> str:
        return normalize_text(value)

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return normalize_value(value)

