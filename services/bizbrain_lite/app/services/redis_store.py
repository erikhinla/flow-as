import json
from collections.abc import Iterable
from typing import Any

from redis.asyncio import Redis

from app.config.settings import get_settings


class RedisStore:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._redis = Redis.from_url(
            self._settings.bizbrain_redis_url,
            decode_responses=True,
        )

    @property
    def redis(self) -> Redis:
        return self._redis

    async def ping(self) -> bool:
        return bool(await self._redis.ping())

    async def set_json(self, key: str, payload: dict[str, Any], ttl_seconds: int | None = None) -> None:
        value = json.dumps(payload, default=str)
        if ttl_seconds:
            await self._redis.set(key, value, ex=ttl_seconds)
            return
        await self._redis.set(key, value)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        value = await self._redis.get(key)
        if not value:
            return None
        return json.loads(value)

    async def append_json_event(self, key: str, payload: dict[str, Any], max_len: int = 1000) -> None:
        encoded = json.dumps(payload, default=str)
        await self._redis.rpush(key, encoded)
        await self._redis.ltrim(key, -max_len, -1)

    async def get_json_events(self, key: str) -> list[dict[str, Any]]:
        entries = await self._redis.lrange(key, 0, -1)
        return [json.loads(entry) for entry in entries]

    async def add_to_set(self, key: str, values: Iterable[str]) -> None:
        if not values:
            return
        await self._redis.sadd(key, *values)

    async def get_set_members(self, key: str) -> list[str]:
        members = await self._redis.smembers(key)
        return sorted(list(members))

    async def close(self) -> None:
        await self._redis.aclose()


redis_store = RedisStore()

