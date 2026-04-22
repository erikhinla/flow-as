from fastapi import Header, HTTPException, status
import jwt

from app.config.settings import get_settings
from app.services.auth_service import decode_access_token


async def require_api_token(x_api_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.bizbrain_api_token:
        return
    if x_api_token != settings.bizbrain_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )
    return authorization.removeprefix("Bearer ").strip()


async def require_jwt(
    authorization: str | None = Header(default=None),
) -> dict:
    """
    FastAPI dependency: validate JWT and return decoded claims.

    Usage::

        @router.get("/protected")
        async def endpoint(claims: dict = Depends(require_jwt)):
            user_id = claims["sub"]
    """
    token = _extract_bearer(authorization)
    try:
        return decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )


def require_tier(*tiers: str):
    """
    Return a FastAPI dependency that enforces a minimum tier.

    Usage::

        @router.get("/mid-only")
        async def endpoint(claims: dict = Depends(require_tier("mid", "concierge"))):
            ...
    """

    async def _check(authorization: str | None = Header(default=None)) -> dict:
        claims = await require_jwt(authorization)
        if claims.get("tier") not in tiers:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This resource requires one of the following tiers: {list(tiers)}.",
            )
        return claims

    return _check

