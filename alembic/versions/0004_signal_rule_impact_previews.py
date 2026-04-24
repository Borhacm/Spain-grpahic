"""signal rule impact previews history

Revision ID: 0004_signal_rule_impact_previews
Revises: 0003_signal_rule_revisions
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_signal_rule_impact_previews"
down_revision = "0003_signal_rule_revisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signal_rule_impact_previews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("signal_rules.id"), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=True),
        sa.Column("limit_series", sa.Integer(), nullable=False),
        sa.Column("override_params_json", sa.JSON(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_signal_rule_impact_previews_rule_id",
        "signal_rule_impact_previews",
        ["rule_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_signal_rule_impact_previews_rule_id", table_name="signal_rule_impact_previews")
    op.drop_table("signal_rule_impact_previews")
