from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .common import BaseRecord, ThreadStateEnum


class ThreadRecord(BaseRecord):
    thread_id: str = Field(default_factory=lambda: f"thread_{uuid4().hex}")
    title: str
    origin: str
    active_task_id: str | None = None
    state: ThreadStateEnum = ThreadStateEnum.OPEN
    tags: list[str] = Field(default_factory=list)
    closed_at: str | None = None


class ThreadCreate(BaseModel):
    title: str
    origin: str
    active_task_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ThreadUpdate(BaseModel):
    title: str | None = None
    active_task_id: str | None = None
    state: ThreadStateEnum | None = None
    tags: list[str] | None = None
    closed_at: str | None = None
    metadata: dict[str, Any] | None = None

