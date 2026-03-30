import asyncio
from typing import Any

from app.schemas.agent_status import AgentHeartbeat, AgentStatusRecord, AgentStatusUpdate
from app.schemas.artifact import ArtifactCreate, ArtifactRecord
from app.schemas.common import AgentStateEnum, now_utc
from app.schemas.handoff import HandoffAck, HandoffCreate, ThreadHandoffRecord
from app.schemas.task import TaskCreate, TaskEvent, TaskRecord, TaskUpdate
from app.schemas.thread import ThreadCreate, ThreadRecord, ThreadUpdate
from app.services.notion_store import notion_store
from app.services.redis_store import redis_store


class RegistryService:
    HEARTBEAT_TTL_SECONDS = 600
    ACTIVE_CACHE_TTL_SECONDS = 72 * 3600

    def _task_key(self, task_id: str) -> str:
        return f"bizbrain:task:{task_id}"

    def _task_event_key(self, task_id: str) -> str:
        return f"bizbrain:task:{task_id}:events"

    def _artifact_key(self, artifact_id: str) -> str:
        return f"bizbrain:artifact:{artifact_id}"

    def _thread_key(self, thread_id: str) -> str:
        return f"bizbrain:thread:{thread_id}"

    def _thread_task_index_key(self, thread_id: str) -> str:
        return f"bizbrain:index:task_by_thread:{thread_id}"

    def _handoff_key(self, handoff_id: str) -> str:
        return f"bizbrain:handoff:{handoff_id}"

    def _agent_status_key(self, agent_id: str) -> str:
        return f"bizbrain:agent:{agent_id}:status"

    async def create_task(self, req: TaskCreate) -> TaskRecord:
        record = TaskRecord(**req.model_dump())
        payload = record.model_dump(mode="json")
        await redis_store.set_json(self._task_key(record.task_id), payload, self.ACTIVE_CACHE_TTL_SECONDS)
        if record.thread_id:
            await redis_store.add_to_set(self._thread_task_index_key(record.thread_id), [record.task_id])
        await self._mirror_safely("task", payload)
        return record

    async def update_task(self, task_id: str, req: TaskUpdate) -> TaskRecord | None:
        existing = await self.get_task(task_id)
        if not existing:
            return None
        updated = existing.model_copy(update={k: v for k, v in req.model_dump().items() if v is not None})
        updated.updated_at = now_utc()
        payload = updated.model_dump(mode="json")
        await redis_store.set_json(self._task_key(task_id), payload, self.ACTIVE_CACHE_TTL_SECONDS)
        if updated.thread_id:
            await redis_store.add_to_set(self._thread_task_index_key(updated.thread_id), [task_id])
        await self._mirror_safely("task", payload)
        return updated

    async def get_task(self, task_id: str) -> TaskRecord | None:
        payload = await redis_store.get_json(self._task_key(task_id))
        if not payload:
            return None
        return TaskRecord.model_validate(payload)

    async def list_tasks(self) -> list[TaskRecord]:
        records: list[TaskRecord] = []
        async for key in redis_store.redis.scan_iter("bizbrain:task:*"):
            if key.endswith(":events"):
                continue
            payload = await redis_store.get_json(key)
            if payload:
                records.append(TaskRecord.model_validate(payload))
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    async def add_task_event(self, task_id: str, event: TaskEvent) -> None:
        await redis_store.append_json_event(self._task_event_key(task_id), event.model_dump(mode="json"))

    async def get_task_events(self, task_id: str) -> list[dict[str, Any]]:
        return await redis_store.get_json_events(self._task_event_key(task_id))

    async def create_artifact(self, req: ArtifactCreate) -> ArtifactRecord:
        record = ArtifactRecord(**req.model_dump())
        payload = record.model_dump(mode="json")
        await redis_store.set_json(self._artifact_key(record.artifact_id), payload, self.ACTIVE_CACHE_TTL_SECONDS)
        await self._mirror_safely("artifact", payload)
        return record

    async def get_artifact(self, artifact_id: str) -> ArtifactRecord | None:
        payload = await redis_store.get_json(self._artifact_key(artifact_id))
        if not payload:
            return None
        return ArtifactRecord.model_validate(payload)

    async def list_artifacts(self) -> list[ArtifactRecord]:
        records: list[ArtifactRecord] = []
        async for key in redis_store.redis.scan_iter("bizbrain:artifact:*"):
            payload = await redis_store.get_json(key)
            if payload:
                records.append(ArtifactRecord.model_validate(payload))
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    async def list_task_artifacts(self, task_id: str) -> list[ArtifactRecord]:
        all_artifacts = await self.list_artifacts()
        return [record for record in all_artifacts if record.task_id == task_id]

    async def create_handoff(self, req: HandoffCreate) -> ThreadHandoffRecord:
        record = ThreadHandoffRecord(**req.model_dump())
        payload = record.model_dump(mode="json")
        await redis_store.set_json(self._handoff_key(record.handoff_id), payload, self.ACTIVE_CACHE_TTL_SECONDS)
        await self._mirror_safely("handoff", payload)
        return record

    async def ack_handoff(self, handoff_id: str, req: HandoffAck) -> ThreadHandoffRecord | None:
        payload = await redis_store.get_json(self._handoff_key(handoff_id))
        if not payload:
            return None
        record = ThreadHandoffRecord.model_validate(payload)
        record.acknowledged_at = req.acknowledged_at
        record.updated_at = now_utc()
        updated = record.model_dump(mode="json")
        await redis_store.set_json(self._handoff_key(handoff_id), updated, self.ACTIVE_CACHE_TTL_SECONDS)
        await self._mirror_safely("handoff", updated)
        return record

    async def list_handoffs(self) -> list[ThreadHandoffRecord]:
        records: list[ThreadHandoffRecord] = []
        async for key in redis_store.redis.scan_iter("bizbrain:handoff:*"):
            payload = await redis_store.get_json(key)
            if payload:
                records.append(ThreadHandoffRecord.model_validate(payload))
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    async def create_thread(self, req: ThreadCreate) -> ThreadRecord:
        record = ThreadRecord(**req.model_dump())
        payload = record.model_dump(mode="json")
        await redis_store.set_json(self._thread_key(record.thread_id), payload, self.ACTIVE_CACHE_TTL_SECONDS)
        await self._mirror_safely(
            "memory",
            {
                "thread_id": record.thread_id,
                "category": "decision",
                "content": f"Thread opened: {record.title}",
                "source": record.origin,
                "status": record.state,
            },
        )
        return record

    async def get_thread(self, thread_id: str) -> ThreadRecord | None:
        payload = await redis_store.get_json(self._thread_key(thread_id))
        if not payload:
            return None
        return ThreadRecord.model_validate(payload)

    async def update_thread(self, thread_id: str, req: ThreadUpdate) -> ThreadRecord | None:
        existing = await self.get_thread(thread_id)
        if not existing:
            return None
        updated = existing.model_copy(update={k: v for k, v in req.model_dump().items() if v is not None})
        updated.updated_at = now_utc()
        payload = updated.model_dump(mode="json")
        await redis_store.set_json(self._thread_key(thread_id), payload, self.ACTIVE_CACHE_TTL_SECONDS)
        return updated

    async def list_agents(self) -> list[AgentStatusRecord]:
        records: list[AgentStatusRecord] = []
        async for key in redis_store.redis.scan_iter("bizbrain:agent:*:status"):
            payload = await redis_store.get_json(key)
            if payload:
                records.append(AgentStatusRecord.model_validate(payload))
        return sorted(records, key=lambda r: r.agent_id)

    async def get_agent(self, agent_id: str) -> AgentStatusRecord | None:
        payload = await redis_store.get_json(self._agent_status_key(agent_id))
        if not payload:
            return None
        return AgentStatusRecord.model_validate(payload)

    async def update_agent_status(self, agent_id: str, req: AgentStatusUpdate) -> AgentStatusRecord:
        existing = await self.get_agent(agent_id)
        if existing:
            merged = existing.model_dump(mode="json")
        else:
            merged = AgentStatusRecord(agent_id=agent_id).model_dump(mode="json")
        merged.update({k: v for k, v in req.model_dump().items() if v is not None})
        merged["heartbeat_at"] = now_utc().isoformat()
        merged["updated_at"] = now_utc().isoformat()
        record = AgentStatusRecord.model_validate(merged)
        payload = record.model_dump(mode="json")
        await redis_store.set_json(self._agent_status_key(agent_id), payload, self.HEARTBEAT_TTL_SECONDS)
        await self._mirror_safely("agent_status", payload)
        return record

    async def heartbeat_agent(self, agent_id: str, req: AgentHeartbeat) -> AgentStatusRecord:
        current = await self.get_agent(agent_id)
        state = current.state if current else AgentStateEnum.BUSY
        update = AgentStatusUpdate(
            state=state,
            current_task_id=req.current_task_id or (current.current_task_id if current else None),
            queue_depth=req.queue_depth if req.queue_depth is not None else (current.queue_depth if current else 0),
            capabilities=current.capabilities if current else [],
            metadata=req.metadata,
        )
        return await self.update_agent_status(agent_id, update)

    async def _mirror_safely(self, entity: str, payload: dict[str, Any]) -> None:
        """Mirror to Notion with retry. Never blocks; failures are swallowed."""
        max_attempts = 3
        delay_seconds = 0.5

        async def _write() -> None:
            if entity == "task":
                await notion_store.write_tasks(payload)
            elif entity == "artifact":
                await notion_store.write_artifacts(payload)
            elif entity == "handoff":
                await notion_store.write_handoffs(payload)
            elif entity == "agent_status":
                await notion_store.write_agent_status(payload)
            elif entity == "memory":
                await notion_store.write_memory(payload)

        for attempt in range(max_attempts):
            try:
                await _write()
                return
            except Exception:
                if attempt < max_attempts - 1:
                    await asyncio.sleep(delay_seconds * (attempt + 1))
            # Lite behavior: never block runtime when durable sink is unavailable.

registry_service = RegistryService()

