from fastapi import APIRouter

from app.config.settings import get_settings
from app.services.notion_store import notion_store
from app.services.redis_store import redis_store

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, bool | str]:
    redis_ok = False
    notion_ok = False

    try:
        redis_ok = await redis_store.ping()
    except Exception:
        redis_ok = False

    try:
        notion_ok = await notion_store.ping() if notion_store.enabled else False
    except Exception:
        notion_ok = False

    return {
        "service": "bizbrain-lite",
        "env": get_settings().bizbrain_env,
        "redis_ok": redis_ok,
        "notion_ok": notion_ok,
    }


@router.get("/capabilities")
async def capabilities() -> dict[str, list[str]]:
    return {
        "registries": ["tasks", "artifacts", "handoffs", "threads", "agents"],
        "runtime_state": ["redis"],
        "durable_memory": ["notion"],
    }

