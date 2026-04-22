"""
Concierge Booking model.

Stores booking requests for the bespoke AI Concierge service (top-tier).
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()

BOOKING_STATUS_PENDING = "pending"
BOOKING_STATUS_CONFIRMED = "confirmed"
BOOKING_STATUS_COMPLETED = "completed"
BOOKING_STATUS_CANCELLED = "cancelled"


class ConciergeBooking(Base):
    """
    Concierge booking record.

    Created when a concierge-tier user submits a booking request.
    Operator confirms the booking manually (or via a future automation layer).
    """

    __tablename__ = "concierge_bookings"

    booking_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), nullable=False, index=True)

    # What the user is asking for (goals, context)
    goals = Column(Text, nullable=False)
    context_data = Column(JSONB, nullable=False, default=dict)

    # Operator notes / deliverables
    operator_notes = Column(Text, nullable=True)

    # Status lifecycle
    status = Column(String(20), nullable=False, default=BOOKING_STATUS_PENDING)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_bookings_user", "user_id"),
        Index("idx_bookings_status", "status"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ConciergeBooking(booking_id={self.booking_id}, user_id={self.user_id},"
            f" status={self.status})>"
        )
