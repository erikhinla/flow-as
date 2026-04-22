"""
Auth API endpoints.

POST /v1/auth/register          - email + password registration
POST /v1/auth/login             - email + password login → JWT
POST /v1/auth/magic-link        - request a magic link (sent to caller for now)
POST /v1/auth/magic-link/verify - exchange magic link token for JWT
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.models.user import TIER_FREE
from app.schemas.auth import (
    LoginRequest,
    MagicLinkRequest,
    MagicLinkVerifyRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user) -> TokenResponse:
    token = auth_service.create_access_token(
        user_id=user.user_id, email=user.email, tier=user.tier
    )
    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        email=user.email,
        tier=user.tier,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db_session)):
    """
    Register a new user with email + password.

    Returns a JWT access token on success.
    """
    existing = await auth_service.get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    user = await auth_service.create_user(
        db, email=payload.email, plain_password=payload.password, tier=TIER_FREE
    )
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    """
    Authenticate with email + password.

    Returns a JWT access token on success.
    """
    user = await auth_service.get_user_by_email(db, payload.email)
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )
    if not auth_service.verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )
    return _token_response(user)


@router.post("/magic-link", status_code=status.HTTP_202_ACCEPTED)
async def request_magic_link(
    payload: MagicLinkRequest, db: AsyncSession = Depends(get_db_session)
):
    """
    Request a magic link for password-less login.

    If the email is not registered, a free-tier account is created automatically.
    The token is returned in the response body (production deployments should
    email it instead and return only ``{"status": "sent"}``).
    """
    user = await auth_service.get_user_by_email(db, payload.email)
    if not user:
        user = await auth_service.create_user(db, email=payload.email, tier=TIER_FREE)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    raw_token = await auth_service.create_magic_link_token(db, user)

    # TODO: in production, send the token via email and return {"status": "sent"}.
    return {"status": "sent", "magic_token": raw_token}


@router.post("/magic-link/verify", response_model=TokenResponse)
async def verify_magic_link(
    payload: MagicLinkVerifyRequest, db: AsyncSession = Depends(get_db_session)
):
    """
    Exchange a magic link token for a JWT access token.

    Tokens are single-use and expire after ``MAGIC_LINK_EXPIRE_MINUTES``.
    """
    user = await auth_service.consume_magic_link_token(db, payload.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired magic link token.",
        )
    return _token_response(user)
