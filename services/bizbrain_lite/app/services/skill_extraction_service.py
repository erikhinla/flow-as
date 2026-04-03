"""
Hermes Skill Extraction Service

Core learning loop for FLOW Agent OS.

Flow:
1. Job completes → reflection written to reflection_records
2. Hermes checks: is pattern extractable?
3. If yes: create/update skill_records
4. Index skill by task_type + context
5. On next similar task: retrieve skill → enrich execution context
6. Track success/failure → update confidence
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4
import logging

from sqlalchemy import select, and_, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flow_job_record import JobRecord, JobStatus
from app.models.flow_reflection_record import ReflectionRecord
from app.models.flow_skill_record import SkillRecord, SkillStatus

logger = logging.getLogger(__name__)


class SkillExtractionService:
    """
    Hermes skill extraction and learning loop.
    
    Responsibilities:
    - Extract reusable patterns from reflections
    - Index skills by task_type and context
    - Retrieve skills for new tasks
    - Update confidence based on outcomes
    """
    
    # Thresholds for extraction
    MIN_PATTERN_LENGTH = 20  # Minimum pattern description length
    MIN_SUCCESS_CONFIDENCE = 0.5  # Start skills at this confidence
    
    # Confidence deltas
    SUCCESS_DELTA = 0.10  # +0.1 on success
    REPEATED_SUCCESS_DELTA = 0.05  # +0.05 on repeated success
    FAILURE_DELTA = -0.15  # -0.15 on failure
    REPEATED_FAILURE_THRESHOLD = 3  # Mark low_confidence after 3 failures
    
    @staticmethod
    async def should_extract_skill(reflection: ReflectionRecord) -> tuple[bool, Dict[str, bool]]:
        """
        Determine if a reflection contains an extractable skill.
        
        Returns:
            (bool, dict) - (should_extract, checks_dict)
        
        Checks:
        - has_pattern: pattern_observed is not null
        - is_repeatable: task_type is in repeatable list
        - success_clear: success_signal is defined
        - tool_sequence_defined: tool_sequence exists with 2+ steps
        - not_one_off: pattern doesn't indicate single-use
        """
        
        repeatable_types = ['classification', 'rewrite', 'content_prep']
        
        checks = {
            'has_pattern': bool(reflection.pattern_observed),
            'is_repeatable': reflection.owner in ['openclaw', 'hermes'],  # These agents do repeatable work
            'success_clear': bool(reflection.success_signal),
            'tool_sequence_defined': (
                bool(reflection.tool_sequence) and 
                len(reflection.tool_sequence) > 1
            ),
            'not_one_off': not (
                reflection.pattern_observed and 
                'specific to this' in reflection.pattern_observed.lower()
            ),
        }
        
        should_extract = all(checks.values())
        
        logger.info(
            f"Skill extraction check for reflection {reflection.reflection_id}: "
            f"extract={should_extract}, checks={checks}"
        )
        
        return should_extract, checks
    
    @staticmethod
    async def extract_skill(
        db: AsyncSession,
        reflection: ReflectionRecord
    ) -> Optional[str]:
        """
        Extract a skill from a reflection.
        
        Logic:
        1. Check if similar skill exists (by task_type + context)
        2. If exists and similar: update (don't duplicate)
        3. If new: create skill_record
        
        Returns:
            skill_id if extracted, None if skipped
        """
        
        # Step 1: Check if similar skill exists
        stmt = select(SkillRecord).where(
            and_(
                SkillRecord.task_type == 'classification',  # TODO: get from reflection
                SkillRecord.context_type == reflection.context_type,
                SkillRecord.status.in_(['active', 'low_confidence'])
            )
        ).order_by(desc(SkillRecord.confidence)).limit(1)
        
        result = await db.execute(stmt)
        existing_skill = result.scalar_one_or_none()
        
        # Step 2: If similar skill exists, update it (reinforce)
        if existing_skill:
            logger.info(f"Updating existing skill {existing_skill.skill_id}")
            
            # Check similarity (simplified: just use confidence boost)
            existing_skill.times_used += 1
            existing_skill.times_succeeded += 1
            existing_skill.confidence = min(1.0, existing_skill.confidence + 0.05)
            existing_skill.last_used_at = datetime.utcnow()
            existing_skill.last_succeeded_at = datetime.utcnow()
            
            # Restore to active if confidence recovered
            if existing_skill.confidence > 0.4 and existing_skill.status == SkillStatus.LOW_CONFIDENCE.value:
                existing_skill.status = SkillStatus.ACTIVE.value
            
            await db.commit()
            return existing_skill.skill_id
        
        # Step 3: Create new skill
        logger.info(f"Creating new skill from reflection {reflection.reflection_id}")
        
        skill_name = f"{reflection.owner}__{reflection.context_type}__{uuid4().hex[:8]}"
        
        new_skill = SkillRecord(
            skill_id=str(uuid4()),
            name=skill_name,
            task_type='classification',  # TODO: derive from reflection or parent job
            context_type=reflection.context_type,
            pattern=reflection.pattern_observed,
            tool_sequence=reflection.tool_sequence,
            success_signal=reflection.success_signal,
            failure_signal=reflection.failure_signal,
            confidence=SkillExtractionService.MIN_SUCCESS_CONFIDENCE,
            times_used=1,
            times_succeeded=1,
            times_failed=0,
            source_reflection_id=reflection.reflection_id,
            status=SkillStatus.ACTIVE.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        db.add(new_skill)
        await db.commit()
        
        logger.info(f"Created skill {new_skill.skill_id} with confidence {new_skill.confidence}")
        
        return new_skill.skill_id
    
    @staticmethod
    async def retrieve_skills_for_task(
        db: AsyncSession,
        task_type: str,
        context_type: Optional[str] = None,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve applicable skills for a new task.
        
        Query by task_type and context_type, ordered by confidence.
        Used to enrich task context before execution.
        
        Returns:
            List of skill dicts with name, pattern, tool_sequence, confidence
        """
        
        # Build query
        filters = [
            SkillRecord.task_type == task_type,
            SkillRecord.status.in_([SkillStatus.ACTIVE.value, SkillStatus.LOW_CONFIDENCE.value])
        ]
        
        if context_type:
            filters.append(SkillRecord.context_type == context_type)
        
        stmt = select(SkillRecord).where(
            and_(*filters)
        ).order_by(desc(SkillRecord.confidence)).limit(limit)
        
        result = await db.execute(stmt)
        skills = result.scalars().all()
        
        logger.info(
            f"Retrieved {len(skills)} skills for task_type={task_type}, context={context_type}"
        )
        
        return [
            {
                'skill_id': s.skill_id,
                'name': s.name,
                'pattern': s.pattern,
                'tool_sequence': s.tool_sequence,
                'confidence': s.confidence,
                'status': 'experimental' if s.confidence < 0.4 else 'trusted',
            }
            for s in skills
        ]
    
    @staticmethod
    async def update_skill_confidence(
        db: AsyncSession,
        skill_id: str,
        task_succeeded: bool
    ) -> None:
        """
        Update a skill's confidence based on task outcome.
        
        On success: +0.1
        On failure: -0.15
        
        Also updates:
        - times_used, times_succeeded/failed
        - last_used_at, last_succeeded_at
        - status (active → low_confidence, or low_confidence → retired)
        """
        
        stmt = select(SkillRecord).where(SkillRecord.skill_id == skill_id)
        result = await db.execute(stmt)
        skill = result.scalar_one_or_none()
        
        if not skill:
            logger.warning(f"Skill {skill_id} not found for confidence update")
            return
        
        logger.info(f"Updating skill {skill_id} confidence: succeeded={task_succeeded}")
        
        # Update counts and timing
        skill.times_used += 1
        skill.last_used_at = datetime.utcnow()
        
        if task_succeeded:
            # Success path
            skill.times_succeeded += 1
            skill.last_succeeded_at = datetime.utcnow()
            skill.confidence = min(1.0, skill.confidence + SkillExtractionService.SUCCESS_DELTA)
            
            # Restore to active if recovered
            if skill.confidence > 0.4 and skill.status == SkillStatus.LOW_CONFIDENCE.value:
                skill.status = SkillStatus.ACTIVE.value
                logger.info(f"Skill {skill_id} recovered to ACTIVE (confidence={skill.confidence})")
        
        else:
            # Failure path
            skill.times_failed += 1
            skill.confidence = max(0.0, skill.confidence + SkillExtractionService.FAILURE_DELTA)
            
            # Mark low confidence after repeated failures
            if skill.times_failed >= SkillExtractionService.REPEATED_FAILURE_THRESHOLD:
                if skill.confidence < 0.4:
                    skill.status = SkillStatus.LOW_CONFIDENCE.value
                    logger.warning(f"Skill {skill_id} marked LOW_CONFIDENCE (confidence={skill.confidence})")
            
            # Retire if very low confidence
            if skill.should_retire():
                skill.status = SkillStatus.RETIRED.value
                logger.warning(f"Skill {skill_id} RETIRED (confidence={skill.confidence}, "
                              f"success_rate={skill.success_rate():.2%})")
        
        await db.commit()
        
        logger.info(f"Skill {skill_id} updated: confidence={skill.confidence}, "
                   f"times_used={skill.times_used}, times_succeeded={skill.times_succeeded}")
    
    @staticmethod
    async def process_pending_reflections(db: AsyncSession) -> Dict[str, int]:
        """
        Process all reflections awaiting skill extraction.
        
        Called periodically (e.g., every 5 minutes) to batch-process reflections.
        
        Returns:
            {extracted: count, skipped: count, errors: count}
        """
        
        logger.info("Starting skill extraction pass...")
        
        # Get reflections pending extraction
        stmt = select(ReflectionRecord).where(
            ReflectionRecord.skill_extraction_attempted == 'N'
        ).order_by(ReflectionRecord.created_at).limit(100)
        
        result = await db.execute(stmt)
        reflections = result.scalars().all()
        
        logger.info(f"Found {len(reflections)} reflections pending extraction")
        
        stats = {'extracted': 0, 'skipped': 0, 'errors': 0}
        
        for reflection in reflections:
            try:
                # Check if extractable
                should_extract, checks = await SkillExtractionService.should_extract_skill(reflection)
                
                if should_extract:
                    # Extract
                    skill_id = await SkillExtractionService.extract_skill(db, reflection)
                    reflection.skill_extraction_attempted = 'Y'
                    reflection.skills_extracted = [skill_id] if skill_id else []
                    stats['extracted'] += 1
                else:
                    # Skip
                    reflection.skill_extraction_attempted = 'Y'
                    stats['skipped'] += 1
                    logger.debug(f"Skipping reflection {reflection.reflection_id}: {checks}")
                
                await db.commit()
            
            except Exception as e:
                logger.error(f"Error processing reflection {reflection.reflection_id}: {e}")
                stats['errors'] += 1
                await db.rollback()
        
        logger.info(f"Skill extraction pass complete: {stats}")
        return stats
