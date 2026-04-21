from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from .common import BaseRecord, ThreadStateEnum
from app.services.input_normalization import normalize_text, normalize_value


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

    @field_validator("title", "origin", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: str) -> str:
        return normalize_text(value)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return [normalize_text(item) for item in value]

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return normalize_value(value)


class ThreadUpdate(BaseModel):
    title: str | None = None
    active_task_id: str | None = None
    state: ThreadStateEnum | None = None
    tags: list[str] | None = None
    closed_at: str | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_text(value)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [normalize_text(item) for item in value]

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        return normalize_value(value)

