from typing import Any

from notion_client import AsyncClient

from app.config.settings import get_settings


class NotionStore:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._enabled = bool(self._settings.notion_api_key)
        self._client = AsyncClient(auth=self._settings.notion_api_key) if self._enabled else None

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def ping(self) -> bool:
        if not self._enabled or not self._client:
            return False
        try:
            await self._client.search(query="BizBrain Lite", page_size=1)
            return True
        except Exception:
            return False

    async def write_tasks(self, payload: dict[str, Any]) -> None:
        await self._create_page(self._settings.notion_tasks_db_id, payload)

    async def write_artifacts(self, payload: dict[str, Any]) -> None:
        await self._create_page(self._settings.notion_artifacts_db_id, payload)

    async def write_handoffs(self, payload: dict[str, Any]) -> None:
        await self._create_page(self._settings.notion_handoffs_db_id, payload)

    async def write_agent_status(self, payload: dict[str, Any]) -> None:
        await self._create_page(self._settings.notion_agent_status_db_id, payload)

    async def write_memory(self, payload: dict[str, Any]) -> None:
        await self._create_page(self._settings.notion_memory_db_id, payload)

    async def _create_page(self, database_id: str, payload: dict[str, Any]) -> None:
        if not self._enabled or not self._client or not database_id:
            return
        properties: dict[str, Any] = {}
        for key, value in payload.items():
            if value is None:
                continue
            val = str(value)
            if key.lower().endswith("id") or key.lower() in {"title", "status", "source", "type", "state"}:
                properties[key] = {"rich_text": [{"text": {"content": val[:2000]}}]}
            else:
                properties[key] = {"rich_text": [{"text": {"content": val[:2000]}}]}
        await self._client.pages.create(
            parent={"database_id": database_id},
            properties=properties,
        )


notion_store = NotionStore()

