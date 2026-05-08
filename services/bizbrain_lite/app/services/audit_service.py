"""
Audit log writing service for FLOW Agent AS.

Records all material actions to audit_logs table.
Called from worker paths, intake, approval endpoints.
"""

import json
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.audit_log import AuditLogEntry, AuditEventType


async def record_audit_event(
    session: AsyncSession,
    event_type: AuditEventType,
    title: str,
    job_id: Optional[str] = None,
    task_id: Optional[str] = None,
    agent: Optional[str] = None,
    action_by: Optional[str] = "system",
    description: Optional[str] = None,
    event_data: Optional[Dict[str, Any]] = None,
    is_production: bool = False,
    requires_human_approval: bool = False,
) -> AuditLogEntry:
    """
    Record an audit event.
    
    Args:
        session: AsyncSession for database writes
        event_type: AuditEventType enum value
        title: Human-readable title of the action
        job_id: Associated job ID (if applicable)
        task_id: Associated task ID (if applicable)
        agent: Agent that performed the action (openclaw, hermes, agent_zero)
        action_by: Who performed the action (system or username)
        description: Detailed description
        event_data: Event-specific metadata (dict)
        is_production: Whether this action affects production
        requires_human_approval: Whether this was high-risk
    
    Returns:
        AuditLogEntry record that was written
    """
    entry = AuditLogEntry(
        event_type=event_type.value if isinstance(event_type, AuditEventType) else event_type,
        title=title,
        job_id=job_id,
        task_id=task_id,
        agent=agent,
        action_by=action_by,
        description=description,
        event_data=event_data,
        is_production='Y' if is_production else 'N',
        requires_human_approval='Y' if requires_human_approval else 'N',
    )
    
    session.add(entry)
    await session.flush()  # Ensure it's written but don't commit yet (caller may batch)
    
    return entry


async def get_audit_trail_for_job(
    session: AsyncSession,
    job_id: str,
) -> list[AuditLogEntry]:
    """
    Retrieve complete audit trail for a job.
    
    Returns all events in chronological order.
    """
    stmt = (
        select(AuditLogEntry)
        .where(AuditLogEntry.job_id == job_id)
        .order_by(AuditLogEntry.created_at)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_audit_trail_for_task(
    session: AsyncSession,
    task_id: str,
) -> list[AuditLogEntry]:
    """
    Retrieve complete audit trail for a task (may span multiple jobs).
    
    Returns all events in chronological order.
    """
    stmt = (
        select(AuditLogEntry)
        .where(AuditLogEntry.task_id == task_id)
        .order_by(AuditLogEntry.created_at)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_production_actions(
    session: AsyncSession,
) -> list[AuditLogEntry]:
    """
    Retrieve all production-impacting actions (compliance view).
    
    Useful for audit and security reviews.
    """
    stmt = (
        select(AuditLogEntry)
        .where(AuditLogEntry.is_production == 'Y')
        .order_by(AuditLogEntry.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_high_risk_actions(
    session: AsyncSession,
) -> list[AuditLogEntry]:
    """
    Retrieve all high-risk actions requiring approval (compliance view).
    """
    stmt = (
        select(AuditLogEntry)
        .where(AuditLogEntry.requires_human_approval == 'Y')
        .order_by(AuditLogEntry.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()
