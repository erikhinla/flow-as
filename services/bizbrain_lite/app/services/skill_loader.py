"""
Skill Loading Service

Loads relevant skills based on task context to enhance LLM performance.
Provides skill-enhanced context for worker execution.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.models.flow_skill_record import SkillRecord, SkillStatus

logger = logging.getLogger(__name__)


class SkillLoader:
    """Loads and formats relevant skills for LLM context"""
    
    @staticmethod
    async def load_relevant_skills(
        session: AsyncSession,
        task_type: str,
        owner: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Load most relevant skills for the given task context.
        
        Args:
            session: Database session
            task_type: Type of task (content_prep, classification, etc.)
            owner: Agent owner (hermes, openclaw, agent_zero)  
            limit: Maximum number of skills to return
            
        Returns:
            List of skill dictionaries with pattern and confidence data
        """
        try:
            # Query for active skills matching context
            query = select(SkillRecord).where(
                and_(
                    SkillRecord.status == SkillStatus.ACTIVE.value,
                    SkillRecord.confidence >= 0.3,  # Only load reasonably confident skills
                )
            ).order_by(
                desc(SkillRecord.confidence),
                desc(SkillRecord.times_used)
            ).limit(limit)
            
            result = await session.execute(query)
            skills = result.scalars().all()
            
            # Convert to context format
            skill_contexts = []
            for skill in skills:
                # Check relevance to task type and owner
                relevance_score = SkillLoader._calculate_relevance(
                    skill, task_type, owner
                )
                
                if relevance_score > 0.1:  # Only include relevant skills
                    skill_contexts.append({
                        'skill_id': skill.skill_id,
                        'pattern': skill.pattern,
                        'confidence': skill.confidence,
                        'times_used': skill.times_used,
                        'times_succeeded': skill.times_succeeded,
                        'relevance_score': relevance_score,
                        'context_type': skill.context_type
                    })
            
            # Sort by relevance score
            skill_contexts.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            logger.debug("Loaded %d relevant skills for task_type=%s owner=%s", 
                        len(skill_contexts), task_type, owner)
            
            return skill_contexts[:limit]
            
        except Exception as e:
            logger.error("Skill loading failed for task_type=%s owner=%s: %s", 
                        task_type, owner, e)
            return []
    
    @staticmethod
    def _calculate_relevance(
        skill: SkillRecord, 
        task_type: str, 
        owner: str
    ) -> float:
        """Calculate relevance score for a skill given the task context"""
        base_score = skill.confidence
        
        # Boost for matching context type
        if skill.context_type and skill.context_type == task_type:
            base_score += 0.3
            
        # Boost for high success rate
        if skill.times_used > 0:
            success_rate = skill.times_succeeded / skill.times_used
            base_score += success_rate * 0.2
            
        # Boost for frequently used skills
        if skill.times_used >= 5:
            base_score += 0.1
            
        return min(base_score, 1.0)  # Cap at 1.0
    
    @staticmethod
    def format_skills_for_prompt(skills: List[Dict[str, Any]]) -> str:
        """Format skills into prompt-friendly text"""
        if not skills:
            return ""
            
        skill_text = "**Relevant Experience Patterns:**\n\n"
        
        for i, skill in enumerate(skills, 1):
            confidence_indicator = "🟢" if skill['confidence'] > 0.7 else "🟡" if skill['confidence'] > 0.4 else "🔴"
            
            skill_text += f"{i}. {confidence_indicator} **Pattern:** {skill['pattern']}\n"
            skill_text += f"   *Success rate: {skill['times_succeeded']}/{skill['times_used']} " \
                         f"(confidence: {skill['confidence']:.2f})*\n\n"
                         
        skill_text += "Use these patterns to inform your approach while adapting to the specific task requirements.\n\n"
        
        return skill_text


class PerformanceContextLoader:
    """Loads performance context for LLM optimization"""
    
    @staticmethod
    async def load_performance_hints(
        session: AsyncSession,
        task_type: str,
        owner: str
    ) -> str:
        """Load performance optimization hints for the task context"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func, and_, case
            from app.models.flow_job_record import JobRecord, JobStatus
            
            # Get recent performance data for this task type + owner
            cutoff = datetime.utcnow() - timedelta(hours=24)
            
            result = await session.execute(
                select(
                    func.count(JobRecord.job_id).label('total_jobs'),
                    func.sum(
                        case(
                            (JobRecord.status == JobStatus.COMPLETED.value, 1),
                            else_=0
                        )
                    ).label('completed_jobs'),
                    func.avg(
                        func.extract('epoch', JobRecord.completed_at - JobRecord.started_at)
                    ).label('avg_execution_time')
                ).where(
                    and_(
                        JobRecord.task_type == task_type,
                        JobRecord.owner == owner,
                        JobRecord.created_at >= cutoff,
                        JobRecord.started_at.isnot(None)
                    )
                )
            )
            
            stats = result.fetchone()
            
            if stats and stats.total_jobs > 0:
                success_rate = (stats.completed_jobs / stats.total_jobs) * 100
                avg_time = stats.avg_execution_time or 0
                
                hints = f"**Performance Context:**\n"
                hints += f"Recent {task_type} tasks: {success_rate:.0f}% success rate, "
                hints += f"avg {avg_time:.1f}s execution time.\n"
                
                if avg_time > 15:
                    hints += "*Optimization tip: Previous tasks took longer - focus on concise, direct outputs.*\n"
                elif success_rate < 90:
                    hints += "*Quality tip: Some recent tasks had issues - double-check requirements.*\n"
                    
                hints += "\n"
                return hints
                
            return ""
            
        except Exception as e:
            logger.error("Performance context loading failed: %s", e)
            return ""