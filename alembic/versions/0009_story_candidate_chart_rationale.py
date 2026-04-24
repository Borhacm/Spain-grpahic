"""story_candidates chart_rationale column

Revision ID: 0009_story_candidate_chart_rationale
Revises: 0008_public_story_facade
Create Date: 2026-04-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = "0009_story_candidate_chart_rationale"
down_revision = "0008_public_story_facade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("story_candidates", sa.Column("chart_rationale", sa.Text(), nullable=True))
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            text(
                """
                UPDATE story_candidates
                SET chart_rationale = chart_spec_json->>'chart_rationale'
                WHERE chart_rationale IS NULL
                  AND chart_spec_json IS NOT NULL
                  AND (chart_spec_json->>'chart_rationale') IS NOT NULL
                """
            )
        )
    else:
        op.execute(
            text(
                """
                UPDATE story_candidates
                SET chart_rationale = json_extract(chart_spec_json, '$.chart_rationale')
                WHERE chart_rationale IS NULL
                  AND chart_spec_json IS NOT NULL
                """
            )
        )


def downgrade() -> None:
    op.drop_column("story_candidates", "chart_rationale")
