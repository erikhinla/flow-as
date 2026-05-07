"""
Automated Learning Loop Service

Handles automatic reflection generation and skill extraction when jobs complete.
Triggered by worker completion events to build organizational memory.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.flow_job_record import JobRecord, JobStatus
from app.models.flow_reflection_record import ReflectionRecord
from app.models.flow_skill_record import SkillRecord
from app.services.skill_extraction_service import SkillExtractionService

logger = logging.getLogger(__name__)


class AutomatedLearningService:
    """Service for automated learning loop execution"""
    
    @staticmethod
    async def trigger_learning_cycle(
        session: AsyncSession, 
        job_id: str, 
        result_pointer: str
    ) -> Optional[str]:
        """
        Automatically generate reflection and extract skills when job completes.
        
        Args:
            session: Database session
            job_id: Completed job ID
            result_pointer: Path to generated artifact
            
        Returns:
            reflection_id if successful, None if skipped
        """
        try:
            # Get job record
            result = await session.execute(
                select(JobRecord).where(JobRecord.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job or job.status != JobStatus.COMPLETED.value:
                return None
                
            # Skip learning for certain task types or owners
            if await AutomatedLearningService._should_skip_learning(job):
                logger.debug("Skipping learning for job_id=%s type=%s", job_id, job.task_type)
                return None
                
            # Generate automated reflection
            reflection_id = await AutomatedLearningService._generate_reflection(
                session, job, result_pointer
            )
            
            if reflection_id:
                # Trigger skill extraction (async, don't wait)
                await AutomatedLearningService._trigger_skill_extraction(session)
                logger.info("Learning cycle triggered for job_id=%s reflection_id=%s", 
                          job_id, reflection_id)
                
            return reflection_id
            
        except Exception as e:
            logger.error("Learning cycle failed for job_id=%s: %s", job_id, e)
            return None
    
    @staticmethod
    async def _should_skip_learning(job: JobRecord) -> bool:
        """Determine if learning should be skipped for this job"""
        skip_types = {"healthcheck"}  # Don't learn from health checks
        return job.task_type in skip_types
    
    @staticmethod
    async def _generate_reflection(
        session: AsyncSession, 
        job: JobRecord, 
        result_pointer: str
    ) -> Optional[str]:
        """Generate automated reflection for completed job"""
        try:
            reflection_id = str(uuid4())
            
            # Analyze job for reflection content
            what_worked = await AutomatedLearningService._analyze_success_patterns(job)
            what_failed = await AutomatedLearningService._analyze_failure_patterns(job)
            pattern_observed = await AutomatedLearningService._identify_patterns(job)
            
            # Create reflection record
            reflection = ReflectionRecord(
                reflection_id=reflection_id,
                task_id=job.task_id or job_id,
                job_id=job.job_id,
                owner=job.owner,
                what_worked=what_worked,
                what_failed=what_failed or "No significant issues identified",
                pattern_observed=pattern_observed,
                context_type=job.task_type,
                sensitivity_level="internal",
                created_at=datetime.utcnow(),
            )
            
            session.add(reflection)
            await session.commit()
            
            logger.info("Auto-reflection created: reflection_id=%s job_id=%s", 
                      reflection_id, job.job_id)
            return reflection_id
            
        except Exception as e:
            logger.error("Reflection generation failed for job_id=%s: %s", job.job_id, e)
            return None
    
    @staticmethod
    async def _analyze_success_patterns(job: JobRecord) -> str:
        """Analyze what worked well in the job execution"""
        execution_time = None
        if job.completed_at and job.started_at:
            execution_time = (job.completed_at - job.started_at).total_seconds()
        
        success_factors = []
        
        # Fast execution
        if execution_time and execution_time < 10:
            success_factors.append("Fast execution under 10 seconds")
            
        # Task type specific patterns
        if job.task_type == "content_prep":
            success_factors.append("Content generation workflow completed successfully")
        elif job.task_type == "classification":
            success_factors.append("Classification task resolved efficiently")
        elif job.task_type == "implementation":
            success_factors.append("Implementation task executed through proper workflow")
            
        # Owner-specific patterns
        if job.owner == "hermes":
            success_factors.append("Hermes content pipeline functioned correctly")
        elif job.owner == "openclaw":
            success_factors.append("OpenClaw routing and classification worked")
        elif job.owner == "agent_zero":
            success_factors.append("Agent Zero high-complexity task handling succeeded")
            
        return "; ".join(success_factors) if success_factors else "Standard task execution completed"
    
    @staticmethod
    async def _analyze_failure_patterns(job: JobRecord) -> Optional[str]:
        """Analyze what could be improved"""
        if job.error_message:
            return f"Error encountered: {job.error_message[:200]}"
            
        # Check for slow execution
        execution_time = None
        if job.completed_at and job.started_at:
            execution_time = (job.completed_at - job.started_at).total_seconds()
            
        if execution_time and execution_time > 30:
            return f"Slow execution ({execution_time:.1f}s) - investigate bottlenecks"
            
        return None
    
    @staticmethod 
    async def _identify_patterns(job: JobRecord) -> Optional[str]:
        """Identify reusable patterns from the job"""
        patterns = []
        
        # Time-based patterns
        if job.completed_at and job.started_at:
            execution_time = (job.completed_at - job.started_at).total_seconds()
            if execution_time < 5:
                patterns.append("Fast turnaround pattern")
            elif execution_time > 20:
                patterns.append("Complex processing pattern")
                
        # Task type patterns
        if job.task_type and job.owner:
            patterns.append(f"{job.task_type} → {job.owner} routing pattern")
            
        return "; ".join(patterns) if patterns else None
    
    @staticmethod
    async def _trigger_skill_extraction(session: AsyncSession) -> None:
        """Trigger skill extraction from recent reflections"""
        try:
            from sqlalchemy import func
            # Get count of unprocessed reflections
            unprocessed_count = await session.scalar(
                select(func.count(ReflectionRecord.reflection_id)).where(
                    ReflectionRecord.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
                )
            )
            
            # Trigger extraction if we have enough new reflections
            if unprocessed_count and unprocessed_count % 5 == 0:  # Every 5 reflections
                logger.info("Triggering skill extraction for %d recent reflections", unprocessed_count)
                # Note: In production, this would trigger an async task
                # For now, just log the trigger
                
        except Exception as e:
            logger.error("Skill extraction trigger failed: %s", e)


class PerformanceAnalyzer:
    """Analyzes patterns across job executions for optimization"""
    
    @staticmethod
    async def analyze_recent_performance(
        session: AsyncSession, 
        hours: int = 24
    ) -> Dict[str, Any]:
        """Analyze performance patterns from recent jobs"""
        try:
            from sqlalchemy import func, and_
            from datetime import timedelta
            
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            # Get job performance metrics
            result = await session.execute(
                select(
                    JobRecord.owner,
                    JobRecord.task_type,
                    JobRecord.status,
                    func.count(JobRecord.job_id).label('count'),
                    func.avg(
                        func.extract('epoch', JobRecord.completed_at - JobRecord.started_at)
                    ).label('avg_execution_time')
                ).where(
                    and_(
                        JobRecord.created_at >= cutoff,
                        JobRecord.started_at.isnot(None)
                    )
                ).group_by(
                    JobRecord.owner, JobRecord.task_type, JobRecord.status
                )
            )
            
            performance_data = []
            for row in result.fetchall():
                performance_data.append({
                    'owner': row.owner,
                    'task_type': row.task_type, 
                    'status': row.status,
                    'count': row.count,
                    'avg_execution_time': float(row.avg_execution_time or 0)
                })
                
            return {
                'analysis_period_hours': hours,
                'cutoff_time': cutoff.isoformat(),
                'performance_metrics': performance_data,
                'total_jobs': sum(row['count'] for row in performance_data)
            }
            
        except Exception as e:
            logger.error("Performance analysis failed: %s", e)
            return {'error': str(e)}