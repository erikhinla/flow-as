"""
Alembic migration: Create FLOW Agent OS durable state tables

This creates:
- job_records: durable job execution state
- reflection_records: post-task reflections for skill extraction
- skill_records: indexed reusable execution patterns
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = 'flow_001_create_durable_state'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create FLOW durable state tables"""
    
    # job_records table
    op.create_table(
        'job_records',
        sa.Column('job_id', sa.String(36), nullable=False),
        sa.Column('task_id', sa.String(36), nullable=False),
        sa.Column('owner', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('task_type', sa.String(20), nullable=False),
        sa.Column('risk_tier', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('result_pointer', sa.Text(), nullable=True),
        sa.Column('review_pointer', sa.Text(), nullable=True),
        sa.Column('rollback_pointer', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('escalation_triggered_at', sa.DateTime(), nullable=True),
        sa.Column('escalation_notified_to', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('job_id'),
    )
    
    # Indexes for job_records
    op.create_index('idx_status', 'job_records', ['status'])
    op.create_index('idx_owner', 'job_records', ['owner'])
    op.create_index('idx_task_type', 'job_records', ['task_type'])
    op.create_index('idx_created_at', 'job_records', ['created_at'])
    op.create_index('idx_owner_status', 'job_records', ['owner', 'status'])
    op.create_index('idx_task_type_status', 'job_records', ['task_type', 'status'])
    
    # reflection_records table
    op.create_table(
        'reflection_records',
        sa.Column('reflection_id', sa.String(36), nullable=False),
        sa.Column('task_id', sa.String(36), nullable=False),
        sa.Column('job_id', sa.String(36), nullable=False),
        sa.Column('owner', sa.String(20), nullable=False),
        sa.Column('what_worked', sa.Text(), nullable=False),
        sa.Column('what_failed', sa.Text(), nullable=False),
        sa.Column('pattern_observed', sa.Text(), nullable=True),
        sa.Column('context_type', sa.String(100), nullable=True),
        sa.Column('tool_sequence', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('success_signal', sa.Text(), nullable=True),
        sa.Column('failure_signal', sa.Text(), nullable=True),
        sa.Column('sensitivity_level', sa.String(20), nullable=False, server_default='internal'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('skill_extraction_attempted', sa.String(1), nullable=False, server_default='N'),
        sa.Column('skills_extracted', postgresql.ARRAY(sa.String()), nullable=True),
        sa.PrimaryKeyConstraint('reflection_id'),
        sa.ForeignKeyConstraint(['job_id'], ['job_records.job_id']),
    )
    
    # Indexes for reflection_records
    op.create_index('idx_owner', 'reflection_records', ['owner'])
    op.create_index('idx_task_id', 'reflection_records', ['task_id'])
    op.create_index('idx_job_id', 'reflection_records', ['job_id'])
    op.create_index('idx_created_at', 'reflection_records', ['created_at'])
    op.create_index('idx_context_type', 'reflection_records', ['context_type'])
    op.create_index('idx_skill_extraction_pending', 'reflection_records', ['skill_extraction_attempted'])
    
    # skill_records table
    op.create_table(
        'skill_records',
        sa.Column('skill_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('task_type', sa.String(20), nullable=False),
        sa.Column('context_type', sa.String(100), nullable=True),
        sa.Column('pattern', sa.Text(), nullable=False),
        sa.Column('tool_sequence', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('success_signal', sa.Text(), nullable=True),
        sa.Column('failure_signal', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('times_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('times_succeeded', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('times_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('last_succeeded_at', sa.DateTime(), nullable=True),
        sa.Column('source_reflection_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('skill_id'),
        sa.ForeignKeyConstraint(['source_reflection_id'], ['reflection_records.reflection_id']),
    )
    
    # Indexes for skill_records
    op.create_index('idx_task_type', 'skill_records', ['task_type'])
    op.create_index('idx_context_type', 'skill_records', ['context_type'])
    op.create_index('idx_status', 'skill_records', ['status'])
    op.create_index('idx_confidence_desc', 'skill_records', ['confidence'])
    op.create_index('idx_task_context_confidence', 'skill_records', ['task_type', 'context_type', 'confidence'])


def downgrade():
    """Drop FLOW durable state tables"""
    
    # Drop indexes (cascaded by table drop)
    op.drop_table('skill_records')
    op.drop_table('reflection_records')
    op.drop_table('job_records')
