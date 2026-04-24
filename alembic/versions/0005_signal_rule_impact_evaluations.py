"""signal rule impact evaluations

Revision ID: 0005_signal_rule_impact_evaluations
Revises: 0004_signal_rule_impact_previews
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_signal_rule_impact_eval"
down_revision = "0004_signal_rule_impact_previews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signal_rule_impact_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("preview_id", sa.Integer(), sa.ForeignKey("signal_rule_impact_previews.id"), nullable=False),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("signal_rules.id"), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=True),
        sa.Column("predicted_json", sa.JSON(), nullable=False),
        sa.Column("actual_json", sa.JSON(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_signal_rule_impact_evaluations_preview_id",
        "signal_rule_impact_evaluations",
        ["preview_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_signal_rule_impact_evaluations_preview_id",
        table_name="signal_rule_impact_evaluations",
    )
    op.drop_table("signal_rule_impact_evaluations")
