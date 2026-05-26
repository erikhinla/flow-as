"""
FLOW Agent AS Job Record Model

Durable state for every job execution.
Stored in Postgres, indexed by status/owner/task_type.
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class JobStatus(str, Enum):
    """Valid job statuses for governed execution."""
    PENDING = "pending"
    VALIDATED = "validated"
    QUEUED = "queued"
    ACTIVE = "active"
    REVIEW_REQUIRED = "review_required"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    ARCHIVED = "archived"


class AgentOwner(str, Enum):
    """Valid agent owners."""
    OPENCLAW = "openclaw"
    HERMES = "hermes"
    AGENT_ZERO = "agent_zero"


class TaskType(str, Enum):
    """Valid task types from schemas/task_envelope.schema.json."""
    CLASSIFICATION = "classification"
    REWRITE = "rewrite"
    CONTENT_PREP = "content_prep"
    ARTIFACT_PRODUCTION = "artifact_production"
    IMPLEMENTATION = "implementation"
    SKILL_EXTRACTION = "skill_extraction"
    HEALTHCHECK = "healthcheck"


class RiskTier(str, Enum):
    """Risk assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Priority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class JobRecord(Base):
    """Durable governed execution record for one task_id."""

    __tablename__ = "job_records"

    # task_id is also used as job_id at intake, making task submission idempotent.
    job_id = Column(String(100), primary_key=True, default=lambda: str(uuid4()))
    task_id = Column(String(100), nullable=False, index=True)

    owner = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default=JobStatus.PENDING.value, index=True)
    task_type = Column(String(40), nullable=False, index=True)
    risk_tier = Column(String(10), nullable=False)
    priority = Column(String(20), nullable=False, default=Priority.NORMAL.value, index=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    result_pointer = Column(Text, nullable=True)
    review_pointer = Column(Text, nullable=True)
    rollback_pointer = Column(Text, nullable=True)

    title = Column(String(500), nullable=True)
    goal = Column(Text, nullable=True)
    source = Column(String(50), nullable=True)
    review_required = Column(Boolean, nullable=False, default=False)
    execution_approval_required = Column(Boolean, nullable=False, default=False)

    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)

    # Claim lease provides one active worker and permits an expired claim to be retried.
    attempt_number = Column(Integer, nullable=False, default=0)
    claimed_by = Column(String(100), nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)

    escalation_triggered_at = Column(DateTime, nullable=True)
    escalation_notified_to = Column(String(255), nullable=True)

    __table_args__ = (
        Index('idx_job_records_status', 'status'),
        Index('idx_job_records_owner', 'owner'),
        Index('idx_job_records_task_type', 'task_type'),
        Index('idx_job_records_created_at', 'created_at'),
        Index('idx_job_records_owner_status', 'owner', 'status'),
        Index('idx_job_records_task_type_status', 'task_type', 'status'),
        Index('idx_job_records_task_id_unique', 'task_id', unique=True),
    )

    def __repr__(self):
        return f"<JobRecord(job_id={self.job_id}, owner={self.owner}, status={self.status})>"

    def is_active(self) -> bool:
        return self.status == JobStatus.ACTIVE.value

    def is_failed(self) -> bool:
        return self.status == JobStatus.FAILED.value

    def can_retry(self) -> bool:
        return self.is_failed() and self.retry_count < self.max_retries

    def is_escalated(self) -> bool:
        return self.status in [JobStatus.DEAD_LETTER.value, JobStatus.ESCALATED.value]
