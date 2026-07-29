"""Persist the task output contract used by the completion gate.

Revision ID: flow_006_add_output_contract
Revises: flow_005_expand_risk_tier
Create Date: 2026-07-29 18:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "flow_006_add_output_contract"
down_revision = "flow_005_expand_risk_tier"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_records", sa.Column("output_required", sa.Text(), nullable=True))
    op.add_column(
        "job_records",
        sa.Column(
            "inputs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "job_records",
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("job_records", "review_required")
    op.drop_column("job_records", "inputs")
    op.drop_column("job_records", "output_required")
