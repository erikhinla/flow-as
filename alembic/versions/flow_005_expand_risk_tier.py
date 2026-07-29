"""flow_005_expand_risk_tier

Revision ID: flow_005_expand_risk_tier
Revises: flow_004_create_audit_logs
Create Date: 2026-07-28 20:16:00.000000

Allow every canonical FLOW risk tier to be stored without truncation.
"""

from alembic import op
import sqlalchemy as sa


revision = "flow_005_expand_risk_tier"
down_revision = "flow_004_create_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "job_records",
        "risk_tier",
        existing_type=sa.String(length=10),
        type_=sa.String(length=64),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "job_records",
        "risk_tier",
        existing_type=sa.String(length=64),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
