"""editorial intelligence layer

Revision ID: 0002_editorial_layer
Revises: 0001_initial
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_editorial_layer"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "story_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("insight", sa.Text(), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("why_it_matters", sa.Text(), nullable=True),
        sa.Column("geography", sa.String(length=100), nullable=True),
        sa.Column("period_label", sa.String(length=100), nullable=True),
        sa.Column("suggested_chart_type", sa.String(length=50), nullable=True),
        sa.Column("chart_spec_json", sa.JSON(), nullable=True),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("dedupe_hash", sa.String(length=255), nullable=False),
        sa.Column("score_total", sa.Numeric(8, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dedupe_hash", name="uq_story_candidate_dedupe_hash"),
    )
    op.create_index("ix_story_candidates_status_score", "story_candidates", ["status", "score_total"])

    op.create_table(
        "signal_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("signal_type", sa.String(length=80), nullable=False),
        sa.Column("params_json", sa.JSON(), nullable=True),
        sa.Column("weight", sa.Numeric(8, 4), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "candidate_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("story_candidates.id"), nullable=False),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("signal_rules.id"), nullable=True),
        sa.Column("signal_type", sa.String(length=80), nullable=False),
        sa.Column("signal_key", sa.String(length=255), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("strength", sa.Numeric(8, 4), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_candidate_signals_signal_type", "candidate_signals", ["signal_type"])

    op.create_table(
        "candidate_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("story_candidates.id"), nullable=False),
        sa.Column("novelty_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("magnitude_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("freshness_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("editorial_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("clarity_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("robustness_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("noise_penalty", sa.Numeric(8, 4), nullable=False),
        sa.Column("total_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("candidate_id"),
    )

    op.create_table(
        "candidate_related_series",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("story_candidates.id"), nullable=False),
        sa.Column("series_id", sa.Integer(), sa.ForeignKey("series.id"), nullable=False),
        sa.Column("relation_type", sa.String(length=50), nullable=False),
    )
    op.create_table(
        "candidate_related_companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("story_candidates.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("relation_type", sa.String(length=50), nullable=False),
    )
    op.create_table(
        "candidate_crosses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("story_candidates.id"), nullable=False),
        sa.Column("left_entity", sa.String(length=255), nullable=False),
        sa.Column("right_entity", sa.String(length=255), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("suggested_angle", sa.Text(), nullable=False),
        sa.Column("suggested_chart_type", sa.String(length=50), nullable=True),
    )
    op.create_table(
        "candidate_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("story_candidates.id"), nullable=False),
        sa.Column("lead_neutral", sa.Text(), nullable=True),
        sa.Column("base_paragraph", sa.Text(), nullable=True),
        sa.Column("analytical_version", sa.Text(), nullable=True),
        sa.Column("short_version", sa.Text(), nullable=True),
        sa.Column("alt_headlines_json", sa.JSON(), nullable=True),
        sa.Column("followup_questions_json", sa.JSON(), nullable=True),
        sa.Column("warnings_json", sa.JSON(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("candidate_id"),
    )
    op.create_table(
        "editorial_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("story_candidates.id"), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("reviewer", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "publication_targets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("adapter_type", sa.String(length=50), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "published_stories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("story_candidates.id"), nullable=False),
        sa.Column("target_id", sa.Integer(), sa.ForeignKey("publication_targets.id"), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("published_stories")
    op.drop_table("publication_targets")
    op.drop_table("editorial_reviews")
    op.drop_table("candidate_drafts")
    op.drop_table("candidate_crosses")
    op.drop_table("candidate_related_companies")
    op.drop_table("candidate_related_series")
    op.drop_table("candidate_scores")
    op.drop_index("ix_candidate_signals_signal_type", table_name="candidate_signals")
    op.drop_table("candidate_signals")
    op.drop_table("signal_rules")
    op.drop_index("ix_story_candidates_status_score", table_name="story_candidates")
    op.drop_table("story_candidates")
