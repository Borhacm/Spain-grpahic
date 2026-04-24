"""public story facade fields

Revision ID: 0008_public_story_facade
Revises: 0007_drop_story_candidate_state
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_public_story_facade"
down_revision = "0007_drop_story_candidate_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("published_stories", sa.Column("slug", sa.String(length=200), nullable=True))
    op.add_column("published_stories", sa.Column("title", sa.String(length=500), nullable=True))
    op.add_column("published_stories", sa.Column("subtitle", sa.Text(), nullable=True))
    op.add_column("published_stories", sa.Column("body", sa.Text(), nullable=True))
    op.add_column("published_stories", sa.Column("chart_spec", sa.JSON(), nullable=True))
    op.add_column("published_stories", sa.Column("topic", sa.String(length=120), nullable=True))
    op.add_column("published_stories", sa.Column("tags", sa.JSON(), nullable=True))
    op.add_column("published_stories", sa.Column("sources", sa.JSON(), nullable=True))
    op.add_column(
        "published_stories",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.execute("UPDATE published_stories SET updated_at = COALESCE(published_at, NOW())")
    op.execute("UPDATE published_stories SET title = COALESCE(title, payload_json->>'title')")
    op.execute(
        "UPDATE published_stories "
        "SET topic = LOWER(NULLIF(payload_json->>'topic', '')) "
        "WHERE payload_json IS NOT NULL"
    )
    op.execute(
        "UPDATE published_stories "
        "SET slug = regexp_replace(lower(coalesce(title, 'story') || '-' || id::text), '[^a-z0-9]+', '-', 'g') "
        "WHERE slug IS NULL"
    )

    op.create_index("ix_published_stories_slug", "published_stories", ["slug"], unique=False)
    op.create_index(
        "ix_published_stories_topic_published_at",
        "published_stories",
        ["topic", "published_at"],
        unique=False,
    )
    op.create_unique_constraint("uq_published_stories_slug", "published_stories", ["slug"])


def downgrade() -> None:
    op.drop_constraint("uq_published_stories_slug", "published_stories", type_="unique")
    op.drop_index("ix_published_stories_topic_published_at", table_name="published_stories")
    op.drop_index("ix_published_stories_slug", table_name="published_stories")

    op.drop_column("published_stories", "updated_at")
    op.drop_column("published_stories", "sources")
    op.drop_column("published_stories", "tags")
    op.drop_column("published_stories", "topic")
    op.drop_column("published_stories", "chart_spec")
    op.drop_column("published_stories", "body")
    op.drop_column("published_stories", "subtitle")
    op.drop_column("published_stories", "title")
    op.drop_column("published_stories", "slug")
