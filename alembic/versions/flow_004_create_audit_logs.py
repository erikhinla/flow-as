"""flow_004_create_audit_logs

Revision ID: flow_004_create_audit_logs
Revises: flow_003_add_priority_column
Create Date: 2025-05-03 16:30:00.000000

Create audit_logs table for compliance and traceability.
Every material action (submission, execution, review, approval) is recorded.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'flow_004_create_audit_logs'
down_revision = 'flow_003_add_priority_column'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create audit_logs table with required indexes."""
    op.create_table(
        'audit_logs',
        sa.Column('audit_id', sa.String(36), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('job_id', sa.String(36), nullable=True),
        sa.Column('task_id', sa.String(36), nullable=True),
        sa.Column('agent', sa.String(50), nullable=True),
        sa.Column('action_by', sa.String(255), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('is_production', sa.String(1), nullable=False, server_default='N'),
        sa.Column('requires_human_approval', sa.String(1), nullable=False, server_default='N'),
        sa.PrimaryKeyConstraint('audit_id')
    )
    
    # Create indexes
    op.create_index('idx_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('idx_audit_logs_job_id', 'audit_logs', ['job_id'])
    op.create_index('idx_audit_logs_task_id', 'audit_logs', ['task_id'])
    op.create_index('idx_audit_logs_agent', 'audit_logs', ['agent'])
    op.create_index('idx_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_logs_is_production', 'audit_logs', ['is_production'])


def downgrade() -> None:
    """Drop audit_logs table."""
    op.drop_index('idx_audit_logs_is_production')
    op.drop_index('idx_audit_logs_created_at')
    op.drop_index('idx_audit_logs_agent')
    op.drop_index('idx_audit_logs_task_id')
    op.drop_index('idx_audit_logs_job_id')
    op.drop_index('idx_audit_logs_event_type')
    op.drop_table('audit_logs')
