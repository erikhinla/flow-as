from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .common import BaseRecord, SourceEnum, TaskStatusEnum, now_utc


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


class TaskUpdate(BaseModel):
    status: TaskStatusEnum | None = None
    priority: int | None = None
    owner_agent: str | None = None
    thread_id: str | None = None
    repo_path: str | None = None
    metadata: dict[str, Any] | None = None


class TaskEvent(BaseModel):
    event_type: str
    detail: str
    source: SourceEnum
    metadata: dict[str, Any] = Field(default_factory=dict)
    at: str = Field(default_factory=lambda: now_utc().isoformat())

