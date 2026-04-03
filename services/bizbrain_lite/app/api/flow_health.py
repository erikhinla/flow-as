"""
FLOW Agent OS Health Check Endpoint

Extended health checks for FLOW's durable state (Postgres job_records, reflections, skills).
Monitors queue depth, worker status, and extraction lag.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flow_job_record import JobRecord, JobStatus, AgentOwner
from app.models.flow_reflection_record import ReflectionRecord
from app.models.flow_skill_record import SkillRecord
from app.config.database import get_db_session

router = APIRouter(tags=["flow-health"], prefix="/flow")


@router.get("/health")
async def flow_health(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """
    FLOW Agent OS health check.
    
    Returns:
    - status: "healthy", "degraded", or "unhealthy"
    - checks: individual component health
    - queues: job queue depths by status
    - metrics: performance indicators
    - alerts: any issues detected
    """
    
    try:
        # Query job queue depths
        stmt = select(JobStatus, func.count()).group_by(JobStatus)
        result = await db.execute(stmt)
        queue_counts = dict(result.all()) if result else {}
        
        # Query reflection lag
        stmt = select(
            func.count(ReflectionRecord.reflection_id)
        ).where(
            ReflectionRecord.skill_extraction_attempted == 'N'
        )
        result = await db.execute(stmt)
        pending_extractions = result.scalar() or 0
        
        # Query skill index health
        stmt = select(func.count(SkillRecord.skill_id)).where(
            SkillRecord.status == 'active'
        )
        result = await db.execute(stmt)
        active_skills = result.scalar() or 0
        
        # Query job completion rate (last 1 hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        stmt = select(func.count(JobRecord.job_id)).where(
            and_(
                JobRecord.completed_at >= one_hour_ago,
                JobRecord.status == 'completed'
            )
        )
        result = await db.execute(stmt)
        jobs_completed_1h = result.scalar() or 0
        
        # Query failure rate
        stmt = select(func.count(JobRecord.job_id)).where(
            and_(
                JobRecord.completed_at >= one_hour_ago,
                JobRecord.status.in_(['failed', 'dead_letter'])
            )
        )
        result = await db.execute(stmt)
        jobs_failed_1h = result.scalar() or 0
        
        # Query dead-letter jobs
        stmt = select(func.count(JobRecord.job_id)).where(
            JobRecord.status == 'dead_letter'
        )
        result = await db.execute(stmt)
        dead_letter_count = result.scalar() or 0
        
        # Query escalated jobs
        stmt = select(func.count(JobRecord.job_id)).where(
            JobRecord.status == 'escalated'
        )
        result = await db.execute(stmt)
        escalated_count = result.scalar() or 0
        
        # Query oldest pending job
        stmt = select(func.min(JobRecord.created_at)).where(
            JobRecord.status == 'pending'
        )
        result = await db.execute(stmt)
        oldest_pending_at = result.scalar()
        oldest_pending_seconds = (
            (datetime.utcnow() - oldest_pending_at).total_seconds()
            if oldest_pending_at
            else None
        )
        
        # Determine health status
        alerts = []
        if dead_letter_count > 1:
            alerts.append(f"Dead-letter queue has {dead_letter_count} jobs")
        if escalated_count > 0:
            alerts.append(f"Escalated queue has {escalated_count} jobs")
        if pending_extractions > 10:
            alerts.append(f"Skill extraction lag: {pending_extractions} reflections pending")
        if oldest_pending_seconds and oldest_pending_seconds > 300:
            alerts.append(f"Oldest pending job: {int(oldest_pending_seconds)}s old")
        
        health_status = "healthy"
        if alerts:
            health_status = "degraded" if len(alerts) <= 2 else "unhealthy"
        
        return {
            "status": health_status,
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": "ok",
                "postgres": "ok",
            },
            "queues": {
                "pending": queue_counts.get(JobStatus.PENDING, 0),
                "queued": queue_counts.get(JobStatus.QUEUED, 0),
                "active": queue_counts.get(JobStatus.ACTIVE, 0),
                "review_required": queue_counts.get(JobStatus.REVIEW_REQUIRED, 0),
                "failed": queue_counts.get(JobStatus.FAILED, 0),
                "dead_letter": dead_letter_count,
                "escalated": escalated_count,
            },
            "metrics": {
                "jobs_completed_1h": jobs_completed_1h,
                "jobs_failed_1h": jobs_failed_1h,
                "reflection_extraction_lag_seconds": pending_extractions * 2,  # Rough estimate
                "pending_extractions": pending_extractions,
                "oldest_pending_job_seconds": oldest_pending_seconds,
                "active_skills": active_skills,
            },
            "alerts": alerts if alerts else None,
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "checks": {
                "database": "error",
                "postgres": "error",
            },
        }


@router.get("/workers")
async def worker_status(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """
    Check worker (agent) status.
    
    Returns active job count per owner (openclaw, hermes, agent_zero).
    """
    
    try:
        workers = {}
        for owner in [AgentOwner.OPENCLAW, AgentOwner.HERMES, AgentOwner.AGENT_ZERO]:
            stmt = select(func.count(JobRecord.job_id)).where(
                and_(
                    JobRecord.owner == owner.value,
                    JobRecord.status == 'active'
                )
            )
            result = await db.execute(stmt)
            active_count = result.scalar() or 0
            
            workers[owner.value] = {
                "status": "ok" if active_count < 10 else "busy",
                "active_jobs": active_count,
            }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "workers": workers,
        }
    
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }


@router.get("/queues/summary")
async def queue_summary(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """
    Get detailed queue summary.
    
    Useful for dashboards and monitoring.
    """
    
    try:
        stmt = select(
            JobStatus,
            func.count(JobRecord.job_id).label('count')
        ).group_by(JobStatus)
        
        result = await db.execute(stmt)
        queues = {row[0].value: row[1] for row in result.all()}
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "queues": queues,
            "total": sum(queues.values()),
        }
    
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }
