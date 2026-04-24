"""editorial consistency and signal idempotency

Revision ID: 0004_editorial_consistency_and_auth
Revises: 0003_signal_rule_revisions
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_editorial_consistency_auth"
down_revision = "0003_signal_rule_revisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE story_candidates SET state = status WHERE state IS DISTINCT FROM status")
    op.create_unique_constraint(
        "uq_candidate_signal_candidate_key",
        "candidate_signals",
        ["candidate_id", "signal_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_candidate_signal_candidate_key", "candidate_signals", type_="unique")
