"""
AI Readiness Report model.

Stores intake answers and the generated AI readiness snapshot for mid-tier users.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()

REPORT_STATUS_PENDING = "pending"
REPORT_STATUS_COMPLETE = "complete"
REPORT_STATUS_ERROR = "error"


class AIReadinessReport(Base):
    """
    Stores intake answers and generated readiness snapshot.

    Generated synchronously in the handler; future work can move generation
    to a background task as complexity grows.
    """

    __tablename__ = "ai_readiness_reports"

    report_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), nullable=False, index=True)

    # Raw intake captured as JSON
    intake_data = Column(JSONB, nullable=False, default=dict)

    # Generated snapshot (markdown summary)
    snapshot_text = Column(Text, nullable=True)

    # Status lifecycle
    status = Column(String(20), nullable=False, default=REPORT_STATUS_PENDING)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_reports_user", "user_id"),
        Index("idx_reports_status", "status"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AIReadinessReport(report_id={self.report_id}, user_id={self.user_id},"
            f" status={self.status})>"
        )
