"""Legacy Hermes skill loop endpoints; worker write-back belongs under /jobs."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_api_token
from app.config.database import get_db_session
from app.models.flow_reflection_record import ReflectionRecord
from app.models.flow_skill_record import SkillRecord
from app.services.skill_extraction_service import SkillExtractionService

router = APIRouter(
    tags=["hermes-skills"], prefix="/hermes", dependencies=[Depends(require_api_token)]
)


class ReflectionCreate(BaseModel):
    task_id: str
    job_id: str
    owner: str
    sequence_number: Optional[int] = None
    what_worked: str
    what_failed: str
    pattern_observed: Optional[str] = None
    context_type: Optional[str] = None
    tool_sequence: Optional[List[str]] = None
    success_signal: Optional[str] = None
    failure_signal: Optional[str] = None
    sensitivity_level: str = 'internal'


class ReflectionResponse(BaseModel):
    reflection_id: str
    task_id: str
    job_id: str
    sequence_number: int
    owner: str
    what_worked: str
    what_failed: str
    pattern_observed: Optional[str]
    context_type: Optional[str]
    created_at: str
    skill_extraction_attempted: str


class SkillResponse(BaseModel):
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
    task_succeeded: bool
    notes: Optional[str] = None


class ExtractionStats(BaseModel):
    extracted: int
    skipped: int
    errors: int


@router.post("/reflections", response_model=ReflectionResponse)
async def write_reflection(reflection: ReflectionCreate, db: AsyncSession = Depends(get_db_session)) -> ReflectionResponse:
    """Compatibility endpoint; governed workers should use /jobs/{task_id}/reflections."""
    if reflection.sequence_number is None:
        next_result = await db.execute(
            select(func.coalesce(func.max(ReflectionRecord.sequence_number), 0) + 1)
            .where(ReflectionRecord.task_id == reflection.task_id)
        )
        sequence_number = next_result.scalar_one()
    else:
        sequence_number = reflection.sequence_number
    existing_result = await db.execute(
        select(ReflectionRecord).where(
            ReflectionRecord.task_id == reflection.task_id,
            ReflectionRecord.sequence_number == sequence_number,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        record = existing
    else:
        record = ReflectionRecord(
            reflection_id=str(uuid4()), task_id=reflection.task_id, job_id=reflection.job_id,
            sequence_number=sequence_number, owner=reflection.owner,
            what_worked=reflection.what_worked, what_failed=reflection.what_failed,
            pattern_observed=reflection.pattern_observed, context_type=reflection.context_type,
            tool_sequence=reflection.tool_sequence, success_signal=reflection.success_signal,
            failure_signal=reflection.failure_signal, sensitivity_level=reflection.sensitivity_level,
            created_at=datetime.utcnow(), skill_extraction_attempted='N',
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
    return ReflectionResponse(
        reflection_id=record.reflection_id, task_id=record.task_id, job_id=record.job_id,
        sequence_number=record.sequence_number, owner=record.owner, what_worked=record.what_worked,
        what_failed=record.what_failed, pattern_observed=record.pattern_observed,
        context_type=record.context_type, created_at=record.created_at.isoformat(),
        skill_extraction_attempted=record.skill_extraction_attempted,
    )


@router.post("/extract-skills", response_model=ExtractionStats)
async def extract_skills(db: AsyncSession = Depends(get_db_session)) -> ExtractionStats:
    stats = await SkillExtractionService.process_pending_reflections(db)
    return ExtractionStats(**stats)


@router.get("/skills", response_model=List[SkillResponse])
async def retrieve_skills(
    task_type: str = 'classification', context_type: Optional[str] = None,
    limit: int = 3, db: AsyncSession = Depends(get_db_session),
) -> List[SkillResponse]:
    skills = await SkillExtractionService.retrieve_skills_for_task(
        db, task_type=task_type, context_type=context_type, limit=limit
    )
    return [SkillResponse(**skill) for skill in skills]


@router.post("/skills/{skill_id}/feedback")
async def update_skill_feedback(
    skill_id: str, feedback: SkillFeedback, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    await SkillExtractionService.update_skill_confidence(db, skill_id=skill_id, task_succeeded=feedback.task_succeeded)
    result = await db.execute(select(SkillRecord).where(SkillRecord.skill_id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found")
    return {
        "skill_id": skill.skill_id, "confidence": skill.confidence, "times_used": skill.times_used,
        "times_succeeded": skill.times_succeeded, "times_failed": skill.times_failed,
        "status": skill.status, "success_rate": f"{skill.success_rate():.2%}",
    }


@router.get("/skills/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: str, db: AsyncSession = Depends(get_db_session)) -> SkillResponse:
    result = await db.execute(select(SkillRecord).where(SkillRecord.skill_id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found")
    return SkillResponse(
        skill_id=skill.skill_id, name=skill.name, task_type=skill.task_type,
        context_type=skill.context_type, pattern=skill.pattern, tool_sequence=skill.tool_sequence,
        confidence=skill.confidence, times_used=skill.times_used,
        times_succeeded=skill.times_succeeded, times_failed=skill.times_failed, status=skill.status,
    )
