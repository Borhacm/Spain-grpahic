"""public_stories: textos de contexto público (sin exponer JSON técnico en fachada)

Revision ID: 0011_public_story_narrative_context
Revises: 0010_public_stories_layer
Create Date: 2026-04-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_public_story_narrative_context"
down_revision = "0010_public_stories_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "public_stories",
        sa.Column("narrative_context_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("public_stories", "narrative_context_json")
