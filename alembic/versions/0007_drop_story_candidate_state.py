"""drop duplicated story candidate state column

Revision ID: 0007_drop_story_candidate_state
Revises: 0006_merge_editorial_heads
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_drop_story_candidate_state"
down_revision = "0006_merge_editorial_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Alembic's default `alembic_version.version_num` is VARCHAR(32), but several revision IDs
    # in this project are longer; widen before stamping those revisions.
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)")
    op.execute("UPDATE story_candidates SET state = status WHERE state IS DISTINCT FROM status")
    op.drop_column("story_candidates", "state")


def downgrade() -> None:
    op.add_column("story_candidates", sa.Column("state", sa.String(length=30), nullable=True))
    op.execute("UPDATE story_candidates SET state = status WHERE state IS NULL")
    op.alter_column("story_candidates", "state", nullable=False)
