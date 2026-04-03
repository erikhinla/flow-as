"""
Agent Zero Execution API

Endpoints for:
- Checking review status (GET /v1/agent-zero/reviews/{job_id}/status)
- Submitting review artifacts (POST /v1/agent-zero/reviews/{job_id}/submit)
- Executing high-risk tasks (POST /v1/agent-zero/execute)
"""

from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.models.flow_job_record import JobRecord, JobStatus
from app.services.review_enforcement_service import ReviewEnforcementService
from sqlalchemy import select

router = APIRouter(tags=["agent-zero"], prefix="/agent-zero")


# ============================================================================
# Pydantic Models
# ============================================================================

class ReviewArtifacts(BaseModel):
    """Input for submitting review artifacts"""
    diff: str = Field(..., description="Unified diff of proposed changes")
    review: str = Field(..., description="Review document with approver signature")
    rollback: str = Field(..., description="Rollback plan with detection and actions")


class ReviewStatus(BaseModel):
    """Review status for a job"""
    job_id: str
    diff_present: bool
    diff_valid: bool
    diff_error: Optional[str] = None
    review_present: bool
    review_valid: bool
    review_error: Optional[str] = None
    review_approver: Optional[Dict[str, str]] = None
    rollback_present: bool
    rollback_valid: bool
    rollback_error: Optional[str] = None
    all_valid: bool
    can_execute: bool
    timestamp: str


class ExecutionRequest(BaseModel):
    """Request to execute high-risk task"""
    job_id: str
    task_id: str
    action: str  # execute, rollback


class ExecutionResponse(BaseModel):
    """Response from execution"""
    status: str  # allowed, blocked
    job_id: str
    message: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/reviews/{job_id}/status", response_model=ReviewStatus)
async def get_review_status(
    job_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> ReviewStatus:
    """
    Check review artifact status for a high-risk task.
    
    Returns status of all three artifacts (diff, review, rollback) and
    whether execution is allowed.
    
    Response:
    {
        "job_id": "job-123",
        "diff_present": true,
        "diff_valid": true,
        "review_present": true,
        "review_valid": true,
        "review_approver": {"name": "erikhinla", "date": "2026-04-03"},
        "rollback_present": true,
        "rollback_valid": true,
        "all_valid": true,
        "can_execute": true
    }
    """
    
    # Check if job exists
    stmt = select(JobRecord).where(JobRecord.job_id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Check review artifacts
    all_valid, status = await ReviewEnforcementService.check_review_artifacts(job_id)
    
    return ReviewStatus(
        job_id=job_id,
        diff_present=status['diff']['present'],
        diff_valid=status['diff']['valid'],
        diff_error=status['diff'].get('error'),
        review_present=status['review']['present'],
        review_valid=status['review']['valid'],
        review_error=status['review'].get('error'),
        review_approver=status['review'].get('approver'),
        rollback_present=status['rollback']['present'],
        rollback_valid=status['rollback']['valid'],
        rollback_error=status['rollback'].get('error'),
        all_valid=all_valid,
        can_execute=all_valid,
        timestamp=datetime.utcnow().isoformat()
    )


@router.post("/reviews/{job_id}/submit")
async def submit_review_artifacts(
    job_id: str,
    artifacts: ReviewArtifacts,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Submit review artifacts for a high-risk task.
    
    All three are required:
    - diff: unified diff showing changes
    - review: review document with approver signature
    - rollback: rollback plan with detection and actions
    
    Input:
    {
        "diff": "--- a/file.py\\n+++ b/file.py\\n...",
        "review": "# Review\\n\\n## What changed\\n...",
        "rollback": "# Rollback Plan\\n\\n## Detection\\n..."
    }
    
    Returns:
    {
        "status": "submitted",
        "job_id": "job-123",
        "artifacts": {
            "diff": "runtime/reviews/job-123/task.diff",
            "review": "runtime/reviews/job-123/task.review",
            "rollback": "runtime/reviews/job-123/task.rollback"
        }
    }
    """
    
    # Check if job exists
    stmt = select(JobRecord).where(JobRecord.job_id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Save artifacts
    try:
        saved_artifacts = await ReviewEnforcementService.save_artifacts(
            job_id,
            artifacts.diff,
            artifacts.review,
            artifacts.rollback
        )
        
        # Update job to mark review artifacts provided
        job.review_pointer = saved_artifacts['review']
        db.add(job)
        await db.commit()
        
        return {
            "status": "submitted",
            "job_id": job_id,
            "artifacts": saved_artifacts,
            "message": "Review artifacts submitted. Execute endpoint will validate."
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to save artifacts: {str(e)}")


@router.post("/execute", response_model=ExecutionResponse)
async def execute_task(
    request: ExecutionRequest,
    db: AsyncSession = Depends(get_db_session)
) -> ExecutionResponse:
    """
    Execute a high-risk task (after review approval).
    
    Gates execution behind review artifact validation:
    1. Check all three artifacts exist
    2. Validate each artifact format and content
    3. Verify approver signature on review document
    4. If all pass: allow execution
    5. If any fail: block and return error
    
    Input:
    {
        "job_id": "job-123",
        "task_id": "task-123",
        "action": "execute"
    }
    
    Response (allowed):
    {
        "status": "allowed",
        "job_id": "job-123",
        "message": "All review artifacts valid. Execution approved."
    }
    
    Response (blocked):
    {
        "status": "blocked",
        "job_id": "job-123",
        "error": "Cannot execute without complete review artifacts. Missing: task.diff, task.review."
    }
    """
    
    # Check if job exists
    stmt = select(JobRecord).where(JobRecord.job_id == request.job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {request.job_id} not found")
    
    # Block if artifacts missing
    can_execute, error_msg = await ReviewEnforcementService.block_if_missing_artifacts(
        request.job_id
    )
    
    if not can_execute:
        return ExecutionResponse(
            status="blocked",
            job_id=request.job_id,
            error=error_msg
        )
    
    # All checks passed: update job status to ACTIVE (execution allowed)
    job.status = JobStatus.ACTIVE.value
    job.started_at = datetime.utcnow()
    db.add(job)
    await db.commit()
    
    return ExecutionResponse(
        status="allowed",
        job_id=request.job_id,
        message="All review artifacts valid. Execution approved and job set to ACTIVE."
    )


@router.get("/reviews/{job_id}/artifacts/{artifact_type}")
async def get_artifact(
    job_id: str,
    artifact_type: str
) -> Dict[str, Any]:
    """
    Retrieve a specific review artifact (diff, review, or rollback).
    
    Returns:
    {
        "job_id": "job-123",
        "artifact_type": "diff",
        "content": "--- a/file.py\\n...",
        "created_at": "2026-04-03T..."
    }
    """
    
    if artifact_type not in ['diff', 'review', 'rollback']:
        raise HTTPException(status_code=400, detail=f"Invalid artifact_type: {artifact_type}")
    
    from app.services.review_enforcement_service import ReviewArtifact
    
    content = ReviewArtifact.load_from_disk(job_id, artifact_type)
    
    if not content:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_type} not found for job {job_id}")
    
    return {
        "job_id": job_id,
        "artifact_type": artifact_type,
        "content": content,
        "path": f"runtime/reviews/{job_id}/task.{artifact_type}"
    }
