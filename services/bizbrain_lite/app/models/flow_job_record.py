"""
FLOW Agent OS Job Record Model

Durable state for every job execution.
Stored in Postgres, indexed by status/owner/task_type.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, String, Text, Index, create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


class JobStatus(str, Enum):
    """Valid job statuses (see docs/QUEUE_HYGIENE.md)"""
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
    """Valid agent owners"""
    OPENCLAW = "openclaw"
    HERMES = "hermes"
    AGENT_ZERO = "agent_zero"


class TaskType(str, Enum):
    """Valid task types (from schemas/task_envelope.schema.json)"""
    CLASSIFICATION = "classification"
    REWRITE = "rewrite"
    CONTENT_PREP = "content_prep"
    IMPLEMENTATION = "implementation"
    SKILL_EXTRACTION = "skill_extraction"
    HEALTHCHECK = "healthcheck"


class RiskTier(str, Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class JobRecord(Base):
    """
    Durable job execution record.
    
    Schema matches /schemas/job_record.schema.json.
    All job transitions are logged here with timestamps.
    """
    
    __tablename__ = "job_records"
    
    # Primary key
    job_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # References
    task_id = Column(String(36), nullable=False, index=True)
    
    # Ownership and classification
    owner = Column(String(20), nullable=False)  # openclaw, hermes, agent_zero
    status = Column(String(20), nullable=False, default=JobStatus.PENDING.value, index=True)
    task_type = Column(String(20), nullable=False, index=True)
    risk_tier = Column(String(10), nullable=False)
    
    # Timing
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Artifacts
    result_pointer = Column(Text, nullable=True)  # Path to output
    review_pointer = Column(Text, nullable=True)  # Path to review artifacts
    rollback_pointer = Column(Text, nullable=True)  # Path to rollback plan
    
    # Retry management
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    
    # Escalation
    escalation_triggered_at = Column(DateTime, nullable=True)
    escalation_notified_to = Column(String(255), nullable=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_status', 'status'),
        Index('idx_owner', 'owner'),
        Index('idx_task_type', 'task_type'),
        Index('idx_created_at', 'created_at'),
        Index('idx_owner_status', 'owner', 'status'),
        Index('idx_task_type_status', 'task_type', 'status'),
    )
    
    def __repr__(self):
        return f"<JobRecord(job_id={self.job_id}, owner={self.owner}, status={self.status})>"
    
    def is_active(self) -> bool:
        """Check if job is currently executing"""
        return self.status == JobStatus.ACTIVE.value
    
    def is_failed(self) -> bool:
        """Check if job failed"""
        return self.status == JobStatus.FAILED.value
    
    def can_retry(self) -> bool:
        """Check if job can be retried"""
        return self.is_failed() and self.retry_count < self.max_retries
    
    def is_escalated(self) -> bool:
        """Check if job is escalated"""
        return self.status in [JobStatus.DEAD_LETTER.value, JobStatus.ESCALATED.value]
