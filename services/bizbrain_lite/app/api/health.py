from fastapi import APIRouter

from app.config.database import health_check as postgres_health_check
from app.config.settings import get_settings
from app.services.redis_store import redis_store

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, bool | str]:
    redis_ok = False
    postgres_ok = False

    try:
        redis_ok = await redis_store.ping()
    except Exception:
        redis_ok = False

    try:
        postgres_ok = await postgres_health_check()
    except Exception:
        postgres_ok = False

    return {
        "service": "bizbrain-lite",
        "env": get_settings().bizbrain_env,
        "redis_ok": redis_ok,
        "postgres_ok": postgres_ok,
    }


@router.get("/capabilities")
async def capabilities() -> dict[str, list[str]]:
    return {
        "registries": ["tasks", "artifacts", "handoffs", "threads", "agents"],
        "runtime_state": ["redis", "postgres"],
        "durable_memory": ["postgres"],
    }

