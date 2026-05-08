"""
Alembic migration: Add priority column to job_records

Adds priority field to support task prioritization and queue ordering.
Priority values: low, normal, high, urgent (default: normal)
"""

from alembic import op
import sqlalchemy as sa

revision = 'flow_003_add_priority_column'
down_revision = 'flow_002_add_goal_title_source'
branch_labels = None
depends_on = None


def upgrade():
    """Add priority column to job_records table"""
    op.add_column('job_records', sa.Column('priority', sa.String(20), nullable=False, server_default='normal'))
    
    # Add index for priority-based queue ordering
    op.create_index('idx_job_records_priority', 'job_records', ['priority'])
    op.create_index('idx_job_records_owner_priority', 'job_records', ['owner', 'priority'])


def downgrade():
    """Remove priority column and indexes"""
    op.drop_index('idx_job_records_owner_priority', 'job_records')
    op.drop_index('idx_job_records_priority', 'job_records')
    op.drop_column('job_records', 'priority')