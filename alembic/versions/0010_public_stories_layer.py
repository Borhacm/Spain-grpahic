"""public_stories: capa limpia entre editorial y fachada web

Revision ID: 0010_public_stories_layer
Revises: 0009_story_candidate_chart_rationale
Create Date: 2026-04-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_public_stories_layer"
down_revision = "0009_story_candidate_chart_rationale"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_stories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("dek", sa.String(length=500), nullable=True),
        sa.Column("body_markdown", sa.Text(), nullable=False, server_default=""),
        sa.Column("topic", sa.String(length=80), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("primary_chart_spec", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("secondary_chart_spec", sa.JSON(), nullable=True),
        sa.Column("chart_type", sa.String(length=50), nullable=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("story_candidates.id"), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=True),
        sa.Column("summary", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("language", sa.String(length=8), nullable=False, server_default="es"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("slug", name="uq_public_stories_slug"),
        sa.UniqueConstraint("candidate_id", name="uq_public_stories_candidate_id"),
        sa.CheckConstraint(
            "(status != 'published') OR (published_at IS NOT NULL)",
            name="ck_public_stories_published_requires_date",
        ),
        sa.CheckConstraint(
            "(status != 'scheduled') OR (scheduled_at IS NOT NULL)",
            name="ck_public_stories_scheduled_requires_date",
        ),
    )
    op.create_index("ix_public_stories_topic", "public_stories", ["topic"], unique=False)
    op.create_index("ix_public_stories_status_published_at", "public_stories", ["status", "published_at"], unique=False)
    op.create_index("ix_public_stories_candidate_id", "public_stories", ["candidate_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_public_stories_candidate_id", table_name="public_stories")
    op.drop_index("ix_public_stories_status_published_at", table_name="public_stories")
    op.drop_index("ix_public_stories_topic", table_name="public_stories")
    op.drop_table("public_stories")
