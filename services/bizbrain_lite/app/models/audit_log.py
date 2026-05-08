"""
FLOW Agent AS Audit Log Model

Immutable compliance record for all agent actions.
Stored in Postgres, indexed for queryability.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from app.models.flow_job_record import Base  # Use shared Base


class AuditEventType(str, Enum):
    """Types of auditable events"""
    JOB_SUBMITTED = "job_submitted"
    JOB_QUEUED = "job_queued"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    REVIEW_REQUESTED = "review_requested"
    REVIEW_ARTIFACT_SUBMITTED = "review_artifact_submitted"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    SKILL_EXTRACTED = "skill_extracted"
    REFLECTION_WRITTEN = "reflection_written"
    ESCALATION_TRIGGERED = "escalation_triggered"


class AuditLogEntry(Base):
    """
    Immutable audit log for compliance and debugging.
    
    Every material action (submission, execution, review, approval) is recorded.
    Cannot be deleted, only archived.
    """
    
    __tablename__ = "audit_logs"
    
    # Primary key
    audit_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Event classification
    event_type = Column(String(50), nullable=False, index=True)
    
    # References
    job_id = Column(String(36), nullable=True, index=True)
    task_id = Column(String(36), nullable=True, index=True)
    
    # Agent/actor
    agent = Column(String(50), nullable=True)  # openclaw, hermes, agent_zero, or human username
    action_by = Column(String(255), nullable=True)  # Who performed the action (system or username)
    
    # Event details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Event-specific metadata (renamed to avoid SQLAlchemy reserved word)
    event_data = Column(JSONB, nullable=True)  # Event-specific data (before/after state, etc.)
    
    # Timing
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Compliance
    is_production = Column(String(1), default='N')  # Y/N flag for production-impacting actions
    requires_human_approval = Column(String(1), default='N')  # Y/N flag for high-risk actions
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_audit_logs_event_type', 'event_type'),
        Index('idx_audit_logs_job_id', 'job_id'),
        Index('idx_audit_logs_task_id', 'task_id'),
        Index('idx_audit_logs_agent', 'agent'),
        Index('idx_audit_logs_created_at', 'created_at'),
        Index('idx_audit_logs_is_production', 'is_production'),
    )
    
    def __repr__(self):
        return f"<AuditLogEntry(audit_id={self.audit_id}, event_type={self.event_type}, job_id={self.job_id})>"
