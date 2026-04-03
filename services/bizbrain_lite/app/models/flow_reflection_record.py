"""
FLOW Agent OS Reflection Record Model

Post-execution reflections for skill extraction.
Stored in Postgres, queryable by task_type/context.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, Index, Float
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import ARRAY

Base = declarative_base()


class SensitivityLevel(str, Enum):
    """Data sensitivity for reflection"""
    PUBLIC = "public"
    INTERNAL = "internal"
    REDACTED = "redacted"


class ReflectionRecord(Base):
    """
    Post-execution reflection record.
    
    Written after every completed job. Used for skill extraction.
    Schema matches /schemas/reflection_record.schema.json.
    """
    
    __tablename__ = "reflection_records"
    
    # Primary key
    reflection_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # References
    task_id = Column(String(36), nullable=False, index=True)
    job_id = Column(String(36), nullable=False, index=True)
    
    # Ownership
    owner = Column(String(20), nullable=False)  # openclaw, hermes, agent_zero
    
    # Reflection content (required)
    what_worked = Column(Text, nullable=False)  # What succeeded
    what_failed = Column(Text, nullable=False)  # What didn't work
    
    # Pattern extraction (optional but valuable)
    pattern_observed = Column(Text, nullable=True)  # Reusable pattern description
    context_type = Column(String(100), nullable=True, index=True)  # e.g., "intake_form", "blog_post"
    tool_sequence = Column(ARRAY(String), nullable=True)  # e.g., ["regex_classify", "markdown_format"]
    success_signal = Column(Text, nullable=True)  # Observable success indicator
    failure_signal = Column(Text, nullable=True)  # Observable failure indicator
    
    # Data sensitivity
    sensitivity_level = Column(String(20), default=SensitivityLevel.INTERNAL.value)
    
    # Timing
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Skill extraction tracking
    skill_extraction_attempted = Column(String(1), default='N')  # Y/N flag
    skills_extracted = Column(ARRAY(String), nullable=True)  # Array of extracted skill IDs
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_owner', 'owner'),
        Index('idx_task_id', 'task_id'),
        Index('idx_job_id', 'job_id'),
        Index('idx_created_at', 'created_at'),
        Index('idx_context_type', 'context_type'),
        Index('idx_skill_extraction_pending', 'skill_extraction_attempted'),
    )
    
    def __repr__(self):
        return f"<ReflectionRecord(reflection_id={self.reflection_id}, job_id={self.job_id})>"
    
    def is_extraction_pending(self) -> bool:
        """Check if skill extraction has been attempted"""
        return self.skill_extraction_attempted == 'N'
    
    def mark_extraction_attempted(self):
        """Mark extraction as attempted"""
        self.skill_extraction_attempted = 'Y'
    
    def has_extractable_pattern(self) -> bool:
        """Check if reflection contains enough info to extract a skill"""
        return (
            bool(self.pattern_observed) and
            bool(self.success_signal) and
            bool(self.tool_sequence) and len(self.tool_sequence) > 1
        )
