"""
FLOW Agent OS Skill Record Model

Reusable execution patterns extracted from reflections.
Indexed by task_type/context, queryable by confidence.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, Index, Float, Integer
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import ARRAY

Base = declarative_base()


class SkillStatus(str, Enum):
    """Skill lifecycle status"""
    ACTIVE = "active"
    LOW_CONFIDENCE = "low_confidence"
    ARCHIVED = "archived"
    RETIRED = "retired"


class SkillRecord(Base):
    """
    Reusable execution pattern / skill.
    
    Extracted from reflections when a repeatable pattern is observed.
    Indexed by task_type and context for fast retrieval on new tasks.
    Schema matches /schemas/skill_record.schema.json.
    """
    
    __tablename__ = "skill_records"
    
    # Primary key
    skill_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Identity
    name = Column(String(100), nullable=False)  # e.g., "intake_form_classification_regex"
    task_type = Column(String(20), nullable=False, index=True)  # classification, rewrite, etc.
    context_type = Column(String(100), nullable=True, index=True)  # e.g., "intake_form"
    
    # Pattern definition (required)
    pattern = Column(Text, nullable=False)  # Description of the reusable approach
    tool_sequence = Column(ARRAY(String), nullable=True)  # Ordered tools/techniques
    success_signal = Column(Text, nullable=True)  # Observable success indicator
    failure_signal = Column(Text, nullable=True)  # Observable failure indicator
    
    # Confidence tracking
    confidence = Column(Float, default=0.5)  # 0.0 to 1.0
    times_used = Column(Integer, default=0)  # How many times applied
    times_succeeded = Column(Integer, default=0)  # Successful uses
    times_failed = Column(Integer, default=0)  # Failed uses
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    last_succeeded_at = Column(DateTime, nullable=True)
    
    # Source and versioning
    source_reflection_id = Column(String(36), nullable=False)  # Which reflection created this
    status = Column(String(20), default=SkillStatus.ACTIVE.value, index=True)
    
    # Timing
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(Integer, default=1)  # Immutable skills; new pattern = new skill
    
    # Indexes for fast retrieval
    __table_args__ = (
        Index('idx_task_type', 'task_type'),
        Index('idx_context_type', 'context_type'),
        Index('idx_status', 'status'),
        Index('idx_confidence_desc', 'confidence'),  # For ordering by confidence
        Index('idx_task_context_confidence', 'task_type', 'context_type', 'confidence'),  # Composite
    )
    
    def __repr__(self):
        return f"<SkillRecord(skill_id={self.skill_id}, name={self.name}, confidence={self.confidence})>"
    
    def is_active(self) -> bool:
        """Check if skill is active and usable"""
        return self.status == SkillStatus.ACTIVE.value
    
    def success_rate(self) -> float:
        """Calculate success rate if skill has been used"""
        if self.times_used == 0:
            return 0.0
        return self.times_succeeded / self.times_used
    
    def should_retire(self) -> bool:
        """Check if skill should be retired (low confidence + repeated failures)"""
        if self.times_used < 5:
            return False  # Need at least 5 uses before retiring
        return (
            self.confidence < 0.2 or
            (self.times_failed > 3 and self.success_rate() < 0.3)
        )
    
    def mark_success(self):
        """Track successful use"""
        self.times_used += 1
        self.times_succeeded += 1
        self.last_used_at = datetime.utcnow()
        self.last_succeeded_at = datetime.utcnow()
        # Increment confidence
        self.confidence = min(1.0, self.confidence + 0.1)
        if self.confidence > 0.4 and self.status == SkillStatus.LOW_CONFIDENCE.value:
            self.status = SkillStatus.ACTIVE.value
    
    def mark_failure(self):
        """Track failed use"""
        self.times_used += 1
        self.times_failed += 1
        self.last_used_at = datetime.utcnow()
        # Decrement confidence
        self.confidence = max(0.0, self.confidence - 0.15)
        if self.confidence < 0.4:
            self.status = SkillStatus.LOW_CONFIDENCE.value
        if self.should_retire():
            self.status = SkillStatus.RETIRED.value
