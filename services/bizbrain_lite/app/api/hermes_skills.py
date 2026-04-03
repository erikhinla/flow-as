"""
Hermes Skill Loop API Endpoints

Endpoints for:
- Writing reflections (POST /reflections)
- Triggering skill extraction (POST /extract-skills)
- Retrieving skills for task enrichment (GET /skills)
- Updating skill confidence (POST /skills/{skill_id}/feedback)
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.models.flow_reflection_record import ReflectionRecord
from app.models.flow_skill_record import SkillRecord
from app.services.skill_extraction_service import SkillExtractionService

router = APIRouter(tags=["hermes-skills"], prefix="/hermes")


# ============================================================================
# Pydantic Models
# ============================================================================

class ReflectionCreate(BaseModel):
    """Input model for writing a reflection"""
    task_id: str
    job_id: str
    owner: str  # openclaw, hermes, agent_zero
    what_worked: str
    what_failed: str
    pattern_observed: Optional[str] = None
    context_type: Optional[str] = None
    tool_sequence: Optional[List[str]] = None
    success_signal: Optional[str] = None
    failure_signal: Optional[str] = None
    sensitivity_level: str = 'internal'


class ReflectionResponse(BaseModel):
    """Output model for a reflection"""
    reflection_id: str
    task_id: str
    job_id: str
    owner: str
    what_worked: str
    what_failed: str
    pattern_observed: Optional[str]
    context_type: Optional[str]
    created_at: str
    skill_extraction_attempted: str


class SkillResponse(BaseModel):
    """Output model for a skill"""
    skill_id: str
    name: str
    task_type: str
    context_type: Optional[str]
    pattern: str
    tool_sequence: Optional[List[str]]
    confidence: float
    times_used: int
    times_succeeded: int
    times_failed: int
    status: str


class SkillFeedback(BaseModel):
    """Input model for skill confidence update"""
    task_succeeded: bool
    notes: Optional[str] = None


class ExtractionStats(BaseModel):
    """Output model for extraction pass stats"""
    extracted: int
    skipped: int
    errors: int


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/reflections", response_model=ReflectionResponse)
async def write_reflection(
    reflection: ReflectionCreate,
    db: AsyncSession = Depends(get_db_session)
) -> ReflectionResponse:
    """
    Write a reflection after task completion.
    
    Called by agents after job completes (success or failure).
    
    Input:
    {
        "task_id": "task-123",
        "job_id": "job-456",
        "owner": "hermes",
        "what_worked": "Regex pattern matched 95% of inputs",
        "what_failed": "Edge cases with special chars",
        "pattern_observed": "Intake submissions follow header+body pattern",
        "context_type": "intake_form",
        "tool_sequence": ["regex_match", "fallback_rule", "json_output"],
        "success_signal": "All files classified with confidence >= 0.9"
    }
    """
    
    reflection_record = ReflectionRecord(
        reflection_id=str(uuid4()),
        task_id=reflection.task_id,
        job_id=reflection.job_id,
        owner=reflection.owner,
        what_worked=reflection.what_worked,
        what_failed=reflection.what_failed,
        pattern_observed=reflection.pattern_observed,
        context_type=reflection.context_type,
        tool_sequence=reflection.tool_sequence,
        success_signal=reflection.success_signal,
        failure_signal=reflection.failure_signal,
        sensitivity_level=reflection.sensitivity_level,
        created_at=datetime.utcnow(),
        skill_extraction_attempted='N',
    )
    
    db.add(reflection_record)
    await db.commit()
    await db.refresh(reflection_record)
    
    return ReflectionResponse(
        reflection_id=reflection_record.reflection_id,
        task_id=reflection_record.task_id,
        job_id=reflection_record.job_id,
        owner=reflection_record.owner,
        what_worked=reflection_record.what_worked,
        what_failed=reflection_record.what_failed,
        pattern_observed=reflection_record.pattern_observed,
        context_type=reflection_record.context_type,
        created_at=reflection_record.created_at.isoformat(),
        skill_extraction_attempted=reflection_record.skill_extraction_attempted,
    )


@router.post("/extract-skills", response_model=ExtractionStats)
async def extract_skills(
    db: AsyncSession = Depends(get_db_session)
) -> ExtractionStats:
    """
    Trigger a skill extraction pass.
    
    Processes all reflections marked as pending extraction.
    Extracts reusable patterns and indexes them by task_type + context.
    
    Returns extraction statistics:
    {
        "extracted": 5,
        "skipped": 2,
        "errors": 0
    }
    
    Call this endpoint periodically (every 5-10 minutes) or on-demand.
    """
    
    stats = await SkillExtractionService.process_pending_reflections(db)
    return ExtractionStats(**stats)


@router.get("/skills", response_model=List[SkillResponse])
async def retrieve_skills(
    task_type: str = 'classification',
    context_type: Optional[str] = None,
    limit: int = 3,
    db: AsyncSession = Depends(get_db_session)
) -> List[SkillResponse]:
    """
    Retrieve skills for task enrichment.
    
    Called before task execution to enrich context with prior skills.
    Returns top-N skills ordered by confidence.
    
    Query parameters:
    - task_type: 'classification', 'rewrite', 'content_prep' (default: 'classification')
    - context_type: optional, e.g., 'intake_form'
    - limit: max results (default: 3)
    
    Example response:
    [
        {
            "skill_id": "skill-123",
            "name": "openclaw__intake_form__abc12345",
            "task_type": "classification",
            "context_type": "intake_form",
            "pattern": "Intake submissions follow predictable header+body pattern",
            "tool_sequence": ["regex_match", "fallback_rule"],
            "confidence": 0.85,
            "times_used": 10,
            "times_succeeded": 9,
            "times_failed": 1,
            "status": "trusted"
        }
    ]
    """
    
    skills = await SkillExtractionService.retrieve_skills_for_task(
        db,
        task_type=task_type,
        context_type=context_type,
        limit=limit
    )
    
    return [SkillResponse(**skill) for skill in skills]


@router.post("/skills/{skill_id}/feedback")
async def update_skill_feedback(
    skill_id: str,
    feedback: SkillFeedback,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Update a skill's confidence based on task outcome.
    
    Called after a task completes to track if the skill helped or hurt.
    
    Input:
    {
        "task_succeeded": true,
        "notes": "Regex pattern worked perfectly on all inputs"
    }
    
    Returns updated skill state.
    """
    
    await SkillExtractionService.update_skill_confidence(
        db,
        skill_id=skill_id,
        task_succeeded=feedback.task_succeeded
    )
    
    # Fetch updated skill
    from sqlalchemy import select
    stmt = select(SkillRecord).where(SkillRecord.skill_id == skill_id)
    result = await db.execute(stmt)
    skill = result.scalar_one_or_none()
    
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found")
    
    return {
        "skill_id": skill.skill_id,
        "confidence": skill.confidence,
        "times_used": skill.times_used,
        "times_succeeded": skill.times_succeeded,
        "times_failed": skill.times_failed,
        "status": skill.status,
        "success_rate": f"{skill.success_rate():.2%}",
    }


@router.get("/skills/{skill_id}")
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> SkillResponse:
    """
    Get a specific skill by ID.
    """
    
    from sqlalchemy import select
    stmt = select(SkillRecord).where(SkillRecord.skill_id == skill_id)
    result = await db.execute(stmt)
    skill = result.scalar_one_or_none()
    
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found")
    
    return SkillResponse(
        skill_id=skill.skill_id,
        name=skill.name,
        task_type=skill.task_type,
        context_type=skill.context_type,
        pattern=skill.pattern,
        tool_sequence=skill.tool_sequence,
        confidence=skill.confidence,
        times_used=skill.times_used,
        times_succeeded=skill.times_succeeded,
        times_failed=skill.times_failed,
        status=skill.status,
    )
