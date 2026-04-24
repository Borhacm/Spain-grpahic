"""signal rule revisions audit trail

Revision ID: 0003_signal_rule_revisions
Revises: 0002_editorial_layer
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_signal_rule_revisions"
down_revision = "0002_editorial_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signal_rule_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("signal_rules.id"), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=True),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_signal_rule_revisions_rule_id", "signal_rule_revisions", ["rule_id"])


def downgrade() -> None:
    op.drop_index("ix_signal_rule_revisions_rule_id", table_name="signal_rule_revisions")
    op.drop_table("signal_rule_revisions")
