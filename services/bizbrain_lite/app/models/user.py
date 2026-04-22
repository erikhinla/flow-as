"""
User and MagicLinkToken models.

Users can authenticate via email+password or magic link.
Tiers control access to Fog Lift Kit, AI Readiness Report, and Concierge.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Tier constants
TIER_FREE = "free"          # Fog Lift Kit access ($7.77 or lead magnet)
TIER_MID = "mid"            # AI Readiness Report ($97–$297)
TIER_CONCIERGE = "concierge"  # Bespoke AI Concierge ($500–$2 000+)


class User(Base):
    """
    Registered user with tier-based access.

    Tier gates:
    - free      → Fog Lift Kit
    - mid       → Fog Lift Kit + AI Readiness Report
    - concierge → all tiers + Concierge booking
    """

    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(Text, nullable=True)  # null when magic-link-only account
    tier = Column(String(20), nullable=False, default=TIER_FREE)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_tier", "tier"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User(user_id={self.user_id}, email={self.email}, tier={self.tier})>"


class MagicLinkToken(Base):
    """
    Single-use magic link token for password-less login.

    Tokens expire after ``MAGIC_LINK_EXPIRE_MINUTES`` and are consumed on first use.
    """

    __tablename__ = "magic_link_tokens"

    token_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    token = Column(String(128), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_magic_tokens_token", "token"),
        Index("idx_magic_tokens_user", "user_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MagicLinkToken(user_id={self.user_id}, used={self.used})>"
