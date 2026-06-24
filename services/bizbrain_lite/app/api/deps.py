"""API dependencies: authentication, database, configuration."""

from fastapi import Depends, HTTPException, Header
from typing import Optional

from app.config.settings import get_settings

settings = get_settings()


async def require_api_token(authorization: Optional[str] = Header(None)) -> str:
    """Require valid API token for protected endpoints.

    Token format: "Bearer {token}"
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = parts[1]
    if token != settings.api_token:
        raise HTTPException(status_code=403, detail="Invalid API token")

    return token
