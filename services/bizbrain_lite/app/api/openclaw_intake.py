"""
OpenClaw Router API Endpoints

Intake for task envelopes:
- POST /intake/task - receive and validate task envelope
- GET /intake/status - check intake health
- GET /queues/status - check all queue depths
- POST /queues/clear - clear a queue (admin)
"""

from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Body, BackgroundTasks
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.services.envelope_validation_service import EnvelopeValidationService, RoutingService
from app.services.input_normalization import normalize_text, normalize_value
from app.services.redis_queue_service import RedisQueueService

router = APIRouter(tags=["openclaw-intake"], prefix="/intake")

# Will be set by dependency injection
redis_queue_service: Optional[RedisQueueService] = None


def get_redis_queue_service() -> RedisQueueService:
    """Dependency injection for Redis queue service"""
    if not redis_queue_service:
        raise HTTPException(status_code=503, detail="Redis queue service not initialized")
    return redis_queue_service


# ============================================================================
# Pydantic Models
# ============================================================================

class TaskEnvelopeInput(BaseModel):
    """Input model for task envelope"""
    task_id: str
    created_at: str
    source: str  # manual, webhook, github_action, scheduled
    title: str
    goal: str
    task_type: str  # classification, rewrite, implementation, etc.
    risk_tier: str  # low, medium, high
    preferred_owner: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    output_required: str
    review_required: Optional[bool] = False
    rollback_required: Optional[bool] = False

    @field_validator("title", "goal", "output_required", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: str) -> str:
        return normalize_text(value)

    @field_validator("inputs", mode="before")
    @classmethod
    def normalize_inputs(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        return normalize_value(value)


class TaskIntakeResponse(BaseModel):
    """Response after task intake"""
    status: str  # accepted, rejected
    job_id: Optional[str] = None
    owner: Optional[str] = None
    queue: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class QueueStatusResponse(BaseModel):
    """Queue status response"""
    timestamp: str
    queues: Dict[str, int]  # {owner: depth}
    total: int


class IntakeStatusResponse(BaseModel):
    """Intake service status"""
    status: str  # healthy, degraded, unhealthy
    timestamp: str
    checks: Dict[str, str]


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/task", response_model=TaskIntakeResponse)
async def intake_task(
    envelope: TaskEnvelopeInput,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    queue_service: RedisQueueService = Depends(get_redis_queue_service)
) -> TaskIntakeResponse:
    """
    Intake a task envelope.
    
    Validates schema and business rules, creates job record, routes to queue.
    
    Input:
    {
        "task_id": "task-123",
        "task_type": "classification",
        "risk_tier": "low",
        "title": "Classify intake submissions",
        "goal": "Classify all intake submissions by type with 95%+ accuracy",
        "source": "webhook",
        "output_required": "JSON file with classifications",
        "review_required": false,
        "inputs": {
            "files": ["submission_1.json", "submission_2.json"],
            "context_refs": ["docs/INTAKE_RULES.md"]
        }
    }
    
    Response (if accepted):
    {
        "status": "accepted",
        "job_id": "task-123",
        "owner": "openclaw",
        "queue": "flow:openclaw:jobs",
        "message": "Task routed to openclaw queue"
    }
    
    Response (if rejected):
    {
        "status": "rejected",
        "error": "High-risk task missing review_required=true"
    }
    """
    
    # Convert input to dict for validation
    envelope_dict = envelope.dict()
    
    # Validate and create job
    success, error_msg, job = await EnvelopeValidationService.validate_and_create_job(
        db,
        envelope_dict,
        source=envelope.source
    )
    
    if not success:
        return TaskIntakeResponse(
            status="rejected",
            error=error_msg
        )
    
    # Route to queue (background task to avoid blocking)
    queue_name = queue_service.get_queue_name(job.owner)
    await queue_service.enqueue_job(job.owner, job.job_id)
    
    # Update job status to QUEUED
    job.status = 'queued'
    db.add(job)
    await db.commit()
    
    return TaskIntakeResponse(
        status="accepted",
        job_id=job.job_id,
        owner=job.owner,
        queue=queue_name,
        message=f"Task routed to {job.owner} queue"
    )


@router.get("/status", response_model=IntakeStatusResponse)
async def intake_status(
    queue_service: RedisQueueService = Depends(get_redis_queue_service)
) -> IntakeStatusResponse:
    """
    Check OpenClaw intake service health.
    
    Returns:
    {
        "status": "healthy",
        "timestamp": "2026-04-03T...",
        "checks": {
            "redis": "ok",
            "database": "ok",
            "schema": "ok"
        }
    }
    """
    
    checks = {}
    
    # Check Redis
    redis_ok = await queue_service.healthcheck()
    checks['redis'] = 'ok' if redis_ok else 'error'
    
    # Check schema
    schema_loaded = bool(EnvelopeValidationService.TASK_ENVELOPE_SCHEMA)
    checks['schema'] = 'ok' if schema_loaded else 'warning'
    
    # Determine overall status
    if all(v == 'ok' for v in checks.values()):
        status = 'healthy'
    elif any(v == 'error' for v in checks.values()):
        status = 'unhealthy'
    else:
        status = 'degraded'
    
    return IntakeStatusResponse(
        status=status,
        timestamp=datetime.utcnow().isoformat(),
        checks=checks
    )


@router.get("/queues/status", response_model=QueueStatusResponse)
async def queue_status(
    queue_service: RedisQueueService = Depends(get_redis_queue_service)
) -> QueueStatusResponse:
    """
    Get status of all job queues.
    
    Returns:
    {
        "timestamp": "2026-04-03T...",
        "queues": {
            "openclaw": 5,
            "hermes": 2,
            "agent_zero": 0
        },
        "total": 7
    }
    """
    
    depths = await queue_service.get_all_queue_depths()
    
    return QueueStatusResponse(
        timestamp=datetime.utcnow().isoformat(),
        queues=depths,
        total=sum(depths.values())
    )


@router.post("/queues/clear")
async def clear_queue(
    owner: str,
    confirm: bool = False,
    queue_service: RedisQueueService = Depends(get_redis_queue_service)
) -> Dict[str, Any]:
    """
    Clear all jobs from a queue (ADMIN ONLY - DESTRUCTIVE).
    
    Query params:
    - owner: openclaw, hermes, or agent_zero
    - confirm: must be true to actually clear
    
    Returns:
    {
        "status": "cleared",
        "queue": "flow:openclaw:jobs",
        "message": "All pending jobs removed"
    }
    """
    
    if not confirm:
        return {
            "status": "not_confirmed",
            "message": "Pass confirm=true to actually clear the queue"
        }
    
    if owner not in ['openclaw', 'hermes', 'agent_zero']:
        raise HTTPException(status_code=400, detail=f"Invalid owner: {owner}")
    
    success = await queue_service.clear_queue(owner)
    
    if success:
        return {
            "status": "cleared",
            "queue": queue_service.get_queue_name(owner),
            "message": "All pending jobs removed (DESTRUCTIVE)"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to clear queue")


@router.get("/dlq")
async def get_dead_letter_queue(
    count: int = 10,
    queue_service: RedisQueueService = Depends(get_redis_queue_service)
) -> Dict[str, Any]:
    """
    Get jobs from dead-letter queue (failed/abandoned tasks).
    
    Query params:
    - count: how many to retrieve (default: 10)
    
    Returns:
    {
        "status": "ok",
        "count": 3,
        "items": [
            {
                "job_id": "job-123",
                "reason": "max retries exceeded",
                "timestamp": "2026-04-03T..."
            }
        ]
    }
    """
    
    items = await queue_service.get_dlq(count=count)
    
    return {
        "status": "ok",
        "count": len(items),
        "items": items
    }
