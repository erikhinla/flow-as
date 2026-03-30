from fastapi import Header, HTTPException, status

from app.config.settings import get_settings


async def require_api_token(x_api_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.bizbrain_api_token:
        return
    if x_api_token != settings.bizbrain_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )

