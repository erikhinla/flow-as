"""Governed task intake and queue visibility endpoints."""

from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_api_token
from app.config.database import get_db_session
from app.services.envelope_validation_service import EnvelopeValidationService, TASK_ENVELOPE_SCHEMA
from app.services.input_normalization import normalize_text, normalize_value
from app.services.redis_queue_service import RedisQueueService
from app.services.audit_service import record_audit_event
from app.models.flow_job_record import JobStatus
from app.models.audit_log import AuditEventType

router = APIRouter(tags=["intake"], prefix="/intake", dependencies=[Depends(require_api_token)])
redis_queue_service: Optional[RedisQueueService] = None


def get_redis_queue_service() -> RedisQueueService:
    if not redis_queue_service:
        raise HTTPException(status_code=503, detail="Redis queue service not initialized")
    return redis_queue_service


class TaskEnvelopeInput(BaseModel):
    task_id: str
    created_at: str
    source: str
    title: str
    goal: str
    task_type: str
    risk_tier: str
    preferred_owner: Optional[str] = None
    owner_role: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    output_required: str
    review_required: bool = False
    execution_approval_required: bool = False
    rollback_required: bool = False
    status: str = "pending"

    @field_validator("title", "goal", "output_required", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: str) -> str:
        return normalize_text(value)

    @field_validator("inputs", mode="before")
    @classmethod
    def normalize_inputs(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        return normalize_value(value)


class TaskIntakeResponse(BaseModel):
    status: str
    job_id: Optional[str] = None
    owner: Optional[str] = None
    queue: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class QueueStatusResponse(BaseModel):
    timestamp: str
    queues: Dict[str, int]
    total: int


class IntakeStatusResponse(BaseModel):
    status: str
    timestamp: str
    checks: Dict[str, str]


@router.post("/task", response_model=TaskIntakeResponse)
async def intake_task(
    envelope: TaskEnvelopeInput,
    db: AsyncSession = Depends(get_db_session),
    queue_service: RedisQueueService = Depends(get_redis_queue_service),
) -> TaskIntakeResponse:
    success, error_msg, job, created_new = await EnvelopeValidationService.validate_and_create_job(
        db, envelope.model_dump(), source=envelope.source
    )
    if not success:
        await record_audit_event(
            db, AuditEventType.JOB_SUBMITTED, f"Task intake rejected: {envelope.title}",
            task_id=envelope.task_id, agent="faas", description=error_msg,
            event_data={"error": error_msg, "task_type": envelope.task_type},
        )
        await db.commit()
        return TaskIntakeResponse(status="rejected", error=error_msg)

    if not created_new:
        return TaskIntakeResponse(
            status="accepted", job_id=job.job_id, owner=job.owner,
            message=f"Idempotent replay: existing job is {job.status}",
        )

    await record_audit_event(
        db, AuditEventType.JOB_SUBMITTED, f"Task intake: {envelope.title}",
        job_id=job.job_id, task_id=job.task_id, agent="faas", action_by=envelope.source,
        description=f"Task submitted for {job.owner}",
        event_data={"task_type": job.task_type, "risk_tier": job.risk_tier},
    )

    if job.owner == 'agent_zero' and job.risk_tier == 'high' and job.execution_approval_required:
        job.status = JobStatus.REVIEW_REQUIRED.value
        await record_audit_event(
            db, AuditEventType.REVIEW_REQUESTED, f"High-risk task held for review: {envelope.title}",
            job_id=job.job_id, task_id=job.task_id, agent="faas",
            description="Execution approval is required before queueing high-risk work",
            event_data={"risk_tier": job.risk_tier}, requires_human_approval=True,
        )
        await db.commit()
        return TaskIntakeResponse(
            status="accepted", job_id=job.job_id, owner=job.owner,
            message="High-risk task accepted and held for execution approval",
        )

    queue_name = queue_service.get_queue_name(job.owner)
    await queue_service.enqueue_job(job.owner, job.job_id)
    job.status = JobStatus.QUEUED.value
    await record_audit_event(
        db, AuditEventType.JOB_QUEUED, f"Task queued for {job.owner}: {envelope.title}",
        job_id=job.job_id, task_id=job.task_id, agent="faas",
        description=f"Task moved to {job.owner} queue for execution",
        event_data={"queue": queue_name, "priority": job.priority},
    )
    await db.commit()
    return TaskIntakeResponse(
        status="accepted", job_id=job.job_id, owner=job.owner, queue=queue_name,
        message=f"Task routed to {job.owner} queue",
    )


@router.get("/status", response_model=IntakeStatusResponse)
async def intake_status(queue_service: RedisQueueService = Depends(get_redis_queue_service)) -> IntakeStatusResponse:
    checks = {
        'redis': 'ok' if await queue_service.healthcheck() else 'error',
        'schema': 'ok' if TASK_ENVELOPE_SCHEMA else 'warning',
    }
    status = 'unhealthy' if 'error' in checks.values() else ('healthy' if all(v == 'ok' for v in checks.values()) else 'degraded')
    return IntakeStatusResponse(status=status, timestamp=datetime.utcnow().isoformat(), checks=checks)


@router.get("/queues/status", response_model=QueueStatusResponse)
async def queue_status(queue_service: RedisQueueService = Depends(get_redis_queue_service)) -> QueueStatusResponse:
    depths = await queue_service.get_all_queue_depths()
    return QueueStatusResponse(timestamp=datetime.utcnow().isoformat(), queues=depths, total=sum(depths.values()))


@router.post("/queues/clear")
async def clear_queue(owner: str, confirm: bool = False, queue_service: RedisQueueService = Depends(get_redis_queue_service)) -> Dict[str, Any]:
    if not confirm:
        return {"status": "not_confirmed", "message": "Pass confirm=true to actually clear the queue"}
    if owner not in EnvelopeValidationService.VALID_OWNERS:
        raise HTTPException(status_code=400, detail=f"Invalid owner: {owner}")
    if not await queue_service.clear_queue(owner):
        raise HTTPException(status_code=500, detail="Failed to clear queue")
    return {"status": "cleared", "queue": queue_service.get_queue_name(owner)}


@router.get("/dlq")
async def get_dead_letter_queue(count: int = 10, queue_service: RedisQueueService = Depends(get_redis_queue_service)) -> Dict[str, Any]:
    items = await queue_service.get_dlq(count=count)
    return {"status": "ok", "count": len(items), "items": items}
