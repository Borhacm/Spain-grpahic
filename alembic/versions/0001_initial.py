"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("auth_type", sa.String(length=50), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_sources_slug", "sources", ["slug"])

    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "geographies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("level", sa.String(length=30), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("geographies.id"), nullable=True),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_geographies_code", "geographies", ["code"])
    op.create_index("ix_geographies_level", "geographies", ["level"])

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"])

    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("topic", sa.String(length=255), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("geography_scope", sa.String(length=100), nullable=True),
        sa.Column("update_frequency", sa.String(length=50), nullable=True),
        sa.Column("license", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("raw_metadata_json", sa.JSON(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "external_id", name="uq_dataset_source_external"),
    )
    op.create_index("ix_datasets_source_id", "datasets", ["source_id"])

    op.create_table(
        "dataset_resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dataset_id", sa.Integer(), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("format", sa.String(length=50), nullable=True),
        sa.Column("download_url", sa.String(length=500), nullable=True),
        sa.Column("raw_metadata_json", sa.JSON(), nullable=True),
        sa.UniqueConstraint("dataset_id", "external_id", name="uq_resource_dataset_external"),
    )

    op.create_table(
        "series",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dataset_id", sa.Integer(), sa.ForeignKey("datasets.id"), nullable=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_code", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=100), nullable=True),
        sa.Column("frequency", sa.String(length=20), nullable=True),
        sa.Column("geography_id", sa.Integer(), sa.ForeignKey("geographies.id"), nullable=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("raw_metadata_json", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "external_code", name="uq_series_source_external"),
    )
    op.create_index("ix_series_external_code", "series", ["external_code"])
    op.create_index("ix_series_source_id", "series", ["source_id"])

    op.create_table(
        "series_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("series_id", sa.Integer(), sa.ForeignKey("series.id"), nullable=False),
        sa.Column("obs_date", sa.Date(), nullable=False),
        sa.Column("obs_value", sa.Numeric(20, 6), nullable=True),
        sa.Column("obs_text", sa.Text(), nullable=True),
        sa.Column("revision_date", sa.Date(), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.UniqueConstraint(
            "series_id", "obs_date", "revision_date", name="uq_series_observation_version"
        ),
    )
    op.create_index("ix_obs_series_date", "series_observations", ["series_id", "obs_date"])

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("company_type", sa.String(length=100), nullable=True),
        sa.Column("is_listed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_confidence", sa.Numeric(4, 3), nullable=True),
    )
    op.create_index("ix_companies_canonical_name", "companies", ["canonical_name"])

    op.create_table(
        "company_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
    )
    op.create_table(
        "company_identifiers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("identifier_type", sa.String(length=50), nullable=False),
        sa.Column("identifier_value", sa.String(length=255), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=True),
        sa.UniqueConstraint("identifier_type", "identifier_value", name="uq_identifier_unique"),
    )
    op.create_table(
        "company_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=100), nullable=True),
        sa.Column("legal_form", sa.String(length=100), nullable=True),
        sa.Column("cnae", sa.String(length=50), nullable=True),
        sa.Column("nace", sa.String(length=50), nullable=True),
        sa.Column("province", sa.String(length=100), nullable=True),
        sa.Column("municipality", sa.String(length=100), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("administrators_json", sa.JSON(), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
    )
    op.create_table(
        "filings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("filing_type", sa.String(length=100), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
    )
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "article_chart_specs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id"), nullable=True),
        sa.Column("series_id", sa.Integer(), sa.ForeignKey("series.id"), nullable=True),
        sa.Column("chart_key", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("spec_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("chart_key"),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "source_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("pipeline_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    tables = [
        "source_runs",
        "tags",
        "article_chart_specs",
        "articles",
        "filings",
        "company_snapshots",
        "company_identifiers",
        "company_aliases",
        "companies",
        "series_observations",
        "series",
        "dataset_resources",
        "datasets",
        "categories",
        "geographies",
        "organizations",
        "sources",
    ]
    for table in tables:
        op.drop_table(table)
