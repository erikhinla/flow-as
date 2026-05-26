"""Worker-facing FAAS lifecycle API for bounded execution and proof write-back."""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_api_token
from app.config.database import get_db_session
from app.models.audit_log import AuditEventType
from app.models.flow_job_record import JobRecord, JobStatus
from app.models.flow_reflection_record import ReflectionRecord
from app.services.audit_service import record_audit_event

router = APIRouter(tags=["worker-jobs"], prefix="/jobs", dependencies=[Depends(require_api_token)])


class ClaimRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=100)
    owner: str = Field(min_length=1, max_length=20)
    lease_seconds: int = Field(default=900, ge=60, le=3600)


class CompletionRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=100)
    result_pointer: str = Field(min_length=1)
    needs_review: bool = False


class FailureRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=100)
    error_message: str = Field(min_length=1)


class EscalationRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1)
    notify_to: Optional[str] = None


class ReflectionRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=100)
    sequence_number: int = Field(ge=1)
    what_worked: str
    what_failed: str
    pattern_observed: Optional[str] = None
    context_type: Optional[str] = None
    tool_sequence: Optional[list[str]] = None
    success_signal: Optional[str] = None
    failure_signal: Optional[str] = None


def job_payload(job: JobRecord) -> Dict[str, Any]:
    return {
        "job_id": job.job_id, "task_id": job.task_id, "owner": job.owner,
        "status": job.status, "task_type": job.task_type, "risk_tier": job.risk_tier,
        "title": job.title, "goal": job.goal, "inputs": job.inputs,
        "output_required": job.output_required, "attempt_number": job.attempt_number,
        "claimed_by": job.claimed_by,
        "lease_expires_at": job.lease_expires_at.isoformat() if job.lease_expires_at else None,
        "result_pointer": job.result_pointer, "review_required": job.review_required,
        "execution_approval_required": job.execution_approval_required,
        "error_message": job.error_message,
    }


async def locked_job(db: AsyncSession, task_id: str) -> JobRecord:
    result = await db.execute(select(JobRecord).where(JobRecord.task_id == task_id).with_for_update())
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Task not found")
    return job


@router.get("/{task_id}")
async def get_job(task_id: str, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    result = await db.execute(select(JobRecord).where(JobRecord.task_id == task_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Task not found")
    return job_payload(job)


@router.post("/{task_id}/claim")
async def claim_job(task_id: str, request: ClaimRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    job = await locked_job(db, task_id)
    now = datetime.utcnow()
    if request.owner != job.owner:
        raise HTTPException(status_code=403, detail="Task is assigned to a different worker owner")
    if job.status == JobStatus.COMPLETED.value:
        return {"outcome": "already_completed", "job": job_payload(job)}
    if job.status == JobStatus.ACTIVE.value and job.lease_expires_at and job.lease_expires_at > now:
        return {"outcome": "already_running", "job": job_payload(job)}
    if job.status not in [JobStatus.QUEUED.value, JobStatus.ACTIVE.value]:
        raise HTTPException(status_code=409, detail=f"Task in state {job.status} cannot be claimed")
    job.status = JobStatus.ACTIVE.value
    job.claimed_by = request.worker_id
    job.attempt_number = (job.attempt_number or 0) + 1
    job.started_at = job.started_at or now
    job.updated_at = now
    job.lease_expires_at = now + timedelta(seconds=request.lease_seconds)
    await record_audit_event(
        db, AuditEventType.JOB_STARTED, f"Worker claimed task: {job.title}", job_id=job.job_id,
        task_id=job.task_id, agent=job.owner, action_by=request.worker_id,
        description="FAAS lease granted for bounded worker execution",
        event_data={"attempt_number": job.attempt_number, "lease_seconds": request.lease_seconds},
    )
    await db.commit()
    return {"outcome": "claimed", "job": job_payload(job)}


@router.post("/{task_id}/complete")
async def complete_job(task_id: str, request: CompletionRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    job = await locked_job(db, task_id)
    if job.status in [JobStatus.COMPLETED.value, JobStatus.REVIEW_REQUIRED.value] and job.result_pointer == request.result_pointer:
        return {"outcome": "already_recorded", "job": job_payload(job)}
    if job.status != JobStatus.ACTIVE.value or job.claimed_by != request.worker_id:
        raise HTTPException(status_code=409, detail="Only the worker holding the active claim may complete this task")
    job.result_pointer = request.result_pointer
    job.status = JobStatus.REVIEW_REQUIRED.value if request.needs_review or job.review_required else JobStatus.COMPLETED.value
    job.completed_at = datetime.utcnow()
    job.lease_expires_at = None
    await record_audit_event(
        db, AuditEventType.JOB_COMPLETED, f"Worker delivered task: {job.title}", job_id=job.job_id,
        task_id=job.task_id, agent=job.owner, action_by=request.worker_id,
        description="Worker result recorded through FAAS API",
        event_data={"result_pointer": request.result_pointer, "status": job.status},
        requires_human_approval=job.status == JobStatus.REVIEW_REQUIRED.value,
    )
    await db.commit()
    return {"outcome": "recorded", "job": job_payload(job)}


@router.post("/{task_id}/fail")
async def fail_job(task_id: str, request: FailureRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    job = await locked_job(db, task_id)
    if job.status != JobStatus.ACTIVE.value or job.claimed_by != request.worker_id:
        raise HTTPException(status_code=409, detail="Only the worker holding the active claim may fail this task")
    job.status = JobStatus.FAILED.value
    job.error_message = request.error_message
    job.lease_expires_at = None
    await record_audit_event(
        db, AuditEventType.JOB_FAILED, f"Worker failed task: {job.title}", job_id=job.job_id,
        task_id=job.task_id, agent=job.owner, action_by=request.worker_id,
        description=request.error_message,
    )
    await db.commit()
    return {"outcome": "recorded", "job": job_payload(job)}


@router.post("/{task_id}/escalate")
async def escalate_job(task_id: str, request: EscalationRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    job = await locked_job(db, task_id)
    if job.status == JobStatus.ACTIVE.value and job.claimed_by != request.worker_id:
        raise HTTPException(status_code=409, detail="Only the worker holding the active claim may escalate this task")
    job.status = JobStatus.ESCALATED.value
    job.error_message = request.reason
    job.escalation_triggered_at = datetime.utcnow()
    job.escalation_notified_to = request.notify_to
    job.lease_expires_at = None
    await record_audit_event(
        db, AuditEventType.ESCALATION_TRIGGERED, f"Worker escalated task: {job.title}", job_id=job.job_id,
        task_id=job.task_id, agent=job.owner, action_by=request.worker_id,
        description=request.reason, event_data={"notify_to": request.notify_to}, requires_human_approval=True,
    )
    await db.commit()
    return {"outcome": "recorded", "job": job_payload(job)}


@router.post("/{task_id}/reflections")
async def write_reflection(task_id: str, request: ReflectionRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    job = await locked_job(db, task_id)
    if job.claimed_by != request.worker_id:
        raise HTTPException(status_code=409, detail="Only the task worker may write its reflection")
    result = await db.execute(select(ReflectionRecord).where(ReflectionRecord.task_id == task_id, ReflectionRecord.sequence_number == request.sequence_number))
    existing = result.scalar_one_or_none()
    if existing:
        return {"outcome": "already_recorded", "reflection_id": existing.reflection_id}
    reflection = ReflectionRecord(
        task_id=job.task_id, job_id=job.job_id, owner=job.owner, sequence_number=request.sequence_number,
        what_worked=request.what_worked, what_failed=request.what_failed,
        pattern_observed=request.pattern_observed, context_type=request.context_type,
        tool_sequence=request.tool_sequence, success_signal=request.success_signal,
        failure_signal=request.failure_signal,
    )
    db.add(reflection)
    await record_audit_event(
        db, AuditEventType.REFLECTION_WRITTEN, f"Reflection written: {job.title}", job_id=job.job_id,
        task_id=job.task_id, agent=job.owner, action_by=request.worker_id,
        event_data={"sequence_number": request.sequence_number},
    )
    await db.commit()
    await db.refresh(reflection)
    return {"outcome": "recorded", "reflection_id": reflection.reflection_id}
