from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from .common import BaseRecord
from app.services.input_normalization import normalize_text, normalize_value


class ArtifactRecord(BaseRecord):
    artifact_id: str = Field(default_factory=lambda: f"artifact_{uuid4().hex}")
    task_id: str
    type: str
    path_or_url: str
    checksum: str | None = None
    producer_agent: str
    campaign: str | None = None


class ArtifactCreate(BaseModel):
    task_id: str
    type: str
    path_or_url: str
    checksum: str | None = None
    producer_agent: str
    campaign: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type", "path_or_url", "producer_agent", "campaign", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_text(value)

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return normalize_value(value)

