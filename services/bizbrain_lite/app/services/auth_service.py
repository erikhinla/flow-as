"""
Auth service: password hashing, JWT creation/verification, magic link management.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.user import MagicLinkToken, User


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def create_access_token(user_id: str, email: str, tier: str) -> str:
    """Return a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "email": email,
        "tier": tier,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    Raises ``jwt.PyJWTError`` on invalid/expired tokens.
    """
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    plain_password: Optional[str] = None,
    tier: str = "free",
) -> User:
    """Create and persist a new user. Returns the saved User."""
    hashed = hash_password(plain_password) if plain_password else None
    user = User(email=email, hashed_password=hashed, tier=tier)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Magic link helpers
# ---------------------------------------------------------------------------


async def create_magic_link_token(db: AsyncSession, user: User) -> str:
    """Generate a magic link token for *user*, persist it, and return the raw token."""
    settings = get_settings()
    raw_token = secrets.token_urlsafe(64)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.magic_link_expire_minutes
    )
    record = MagicLinkToken(
        user_id=user.user_id,
        token=raw_token,
        expires_at=expires_at,
    )
    db.add(record)
    await db.commit()
    return raw_token


async def consume_magic_link_token(
    db: AsyncSession, raw_token: str
) -> Optional[User]:
    """
    Validate and consume a magic link token.

    Returns the associated User on success, None on invalid/expired/used token.
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(MagicLinkToken).where(MagicLinkToken.token == raw_token)
    )
    record: Optional[MagicLinkToken] = result.scalar_one_or_none()

    if record is None or record.used:
        return None
    # Compare naive/aware carefully — store is naive UTC, now is aware UTC
    expires_naive = record.expires_at
    if expires_naive.tzinfo is None:
        expires_aware = expires_naive.replace(tzinfo=timezone.utc)
    else:
        expires_aware = expires_naive
    if now > expires_aware:
        return None

    # Mark consumed
    record.used = True
    db.add(record)
    await db.commit()

    return await get_user_by_id(db, record.user_id)
