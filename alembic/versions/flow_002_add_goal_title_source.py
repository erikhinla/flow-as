"""
Alembic migration: Add goal, title, source columns to job_records

Enables workers to read task context directly from Postgres
without needing to re-fetch the original envelope.
"""

from alembic import op
import sqlalchemy as sa

revision = 'flow_002_add_goal_title_source'
down_revision = 'flow_001_create_durable_state'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('job_records', sa.Column('title', sa.String(500), nullable=True))
    op.add_column('job_records', sa.Column('goal', sa.Text(), nullable=True))
    op.add_column('job_records', sa.Column('source', sa.String(50), nullable=True))


def downgrade():
    op.drop_column('job_records', 'source')
    op.drop_column('job_records', 'goal')
    op.drop_column('job_records', 'title')
