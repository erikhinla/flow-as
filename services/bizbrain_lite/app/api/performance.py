"""
Performance Analysis API

Endpoints for analyzing system performance and learning patterns.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.services.automated_learning_service import PerformanceAnalyzer

router = APIRouter(tags=["performance"], prefix="/performance")


class PerformanceAnalysisResponse(BaseModel):
    """Response model for performance analysis"""
    analysis_period_hours: int
    cutoff_time: str
    performance_metrics: list
    total_jobs: int
    success_rate: float
    avg_execution_time: float
    recommendations: list


@router.get("/analysis", response_model=Dict[str, Any])
async def get_performance_analysis(
    hours: int = Query(default=24, ge=1, le=168, description="Analysis period in hours"),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get performance analysis for the specified time period.
    
    Returns metrics on job execution, success rates, timing, and optimization recommendations.
    """
    analysis_data = await PerformanceAnalyzer.analyze_recent_performance(db, hours)
    
    if 'error' in analysis_data:
        return analysis_data
        
    # Calculate aggregate metrics
    total_jobs = analysis_data.get('total_jobs', 0)
    performance_metrics = analysis_data.get('performance_metrics', [])
    
    # Calculate overall success rate
    completed_jobs = sum(
        metric['count'] for metric in performance_metrics 
        if metric['status'] == 'completed'
    )
    success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
    
    # Calculate overall avg execution time
    execution_times = [
        metric['avg_execution_time'] * metric['count'] 
        for metric in performance_metrics 
        if metric['status'] == 'completed' and metric['avg_execution_time'] > 0
    ]
    avg_execution_time = (
        sum(execution_times) / completed_jobs 
        if completed_jobs > 0 and execution_times 
        else 0
    )
    
    # Generate recommendations
    recommendations = []
    
    if success_rate < 95:
        recommendations.append("Success rate below 95% - investigate failing jobs")
    if avg_execution_time > 20:
        recommendations.append("Average execution time > 20s - optimize for performance")
    if total_jobs == 0:
        recommendations.append("No recent jobs - system may be idle")
        
    # Add owner-specific recommendations
    owner_metrics = {}
    for metric in performance_metrics:
        owner = metric['owner']
        if owner not in owner_metrics:
            owner_metrics[owner] = {'completed': 0, 'failed': 0, 'total_time': 0}
            
        if metric['status'] == 'completed':
            owner_metrics[owner]['completed'] += metric['count']
            owner_metrics[owner]['total_time'] += metric['avg_execution_time'] * metric['count']
        elif metric['status'] == 'failed':
            owner_metrics[owner]['failed'] += metric['count']
    
    for owner, stats in owner_metrics.items():
        total_owner_jobs = stats['completed'] + stats['failed']
        if total_owner_jobs > 0:
            owner_success_rate = stats['completed'] / total_owner_jobs * 100
            if owner_success_rate < 90:
                recommendations.append(f"{owner} agent success rate low ({owner_success_rate:.1f}%)")
                
            if stats['completed'] > 0:
                owner_avg_time = stats['total_time'] / stats['completed']
                if owner_avg_time > 25:
                    recommendations.append(f"{owner} agent slow execution ({owner_avg_time:.1f}s avg)")
    
    return {
        **analysis_data,
        'success_rate': success_rate,
        'avg_execution_time': avg_execution_time,
        'recommendations': recommendations,
        'analysis_generated_at': datetime.utcnow().isoformat()
    }


@router.get("/skills/effectiveness")
async def get_skill_effectiveness(
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Analyze skill effectiveness and learning patterns.
    """
    try:
        from sqlalchemy import select, func, desc
        from app.models.flow_skill_record import SkillRecord, SkillStatus
        
        # Get skill effectiveness metrics
        result = await db.execute(
            select(
                SkillRecord.skill_id,
                SkillRecord.pattern,
                SkillRecord.confidence,
                SkillRecord.times_used,
                SkillRecord.times_succeeded,
                SkillRecord.context_type,
                SkillRecord.status,
                SkillRecord.updated_at
            ).where(
                SkillRecord.status == SkillStatus.ACTIVE.value
            ).order_by(
                desc(SkillRecord.confidence),
                desc(SkillRecord.times_used)
            ).limit(20)
        )
        
        skills = []
        for row in result.fetchall():
            success_rate = (row.times_succeeded / row.times_used * 100) if row.times_used > 0 else 0
            skills.append({
                'skill_id': row.skill_id,
                'pattern': row.pattern[:100] + "..." if len(row.pattern) > 100 else row.pattern,
                'confidence': row.confidence,
                'times_used': row.times_used,
                'times_succeeded': row.times_succeeded,
                'success_rate': success_rate,
                'context_type': row.context_type,
                'last_updated': row.updated_at.isoformat() if row.updated_at else None
            })
        
        # Calculate aggregate skill metrics
        total_skills = len(skills)
        high_confidence_skills = sum(1 for s in skills if s['confidence'] > 0.7)
        frequently_used_skills = sum(1 for s in skills if s['times_used'] >= 5)
        
        return {
            'total_active_skills': total_skills,
            'high_confidence_skills': high_confidence_skills,
            'frequently_used_skills': frequently_used_skills,
            'top_skills': skills[:10],
            'skill_distribution': {
                'high_confidence': high_confidence_skills,
                'medium_confidence': sum(1 for s in skills if 0.4 <= s['confidence'] <= 0.7),
                'low_confidence': sum(1 for s in skills if s['confidence'] < 0.4)
            },
            'generated_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {'error': f'Skill effectiveness analysis failed: {str(e)}'}


@router.post("/skills/cleanup")
async def cleanup_low_performing_skills(
    min_confidence: float = Query(default=0.2, ge=0.0, le=1.0),
    min_success_rate: float = Query(default=0.3, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Mark low-performing skills as inactive based on confidence and success rate thresholds.
    """
    try:
        from sqlalchemy import select, update
        from app.models.flow_skill_record import SkillRecord, SkillStatus
        
        # Find low-performing skills
        result = await db.execute(
            select(SkillRecord).where(
                SkillRecord.status == SkillStatus.ACTIVE.value
            )
        )
        
        skills_to_deactivate = []
        for skill in result.scalars().all():
            success_rate = (skill.times_succeeded / skill.times_used) if skill.times_used > 0 else 0
            
            if (skill.confidence < min_confidence or 
                (skill.times_used >= 3 and success_rate < min_success_rate)):
                skills_to_deactivate.append(skill.skill_id)
        
        # Deactivate low-performing skills
        if skills_to_deactivate:
            await db.execute(
                update(SkillRecord)
                .where(SkillRecord.skill_id.in_(skills_to_deactivate))
                .values(status=SkillStatus.INACTIVE.value, updated_at=datetime.utcnow())
            )
            await db.commit()
        
        return {
            'deactivated_skills': len(skills_to_deactivate),
            'skill_ids': skills_to_deactivate,
            'cleanup_criteria': {
                'min_confidence': min_confidence,
                'min_success_rate': min_success_rate
            },
            'cleanup_completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        await db.rollback()
        return {'error': f'Skill cleanup failed: {str(e)}'}