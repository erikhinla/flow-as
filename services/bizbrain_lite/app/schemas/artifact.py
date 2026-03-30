from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .common import BaseRecord


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

