from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(50), default="api")
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auth_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    runs: Mapped[list[SourceRun]] = relationship(back_populates="source")
    datasets: Mapped[list[Dataset]] = relationship(back_populates="source")
    series: Mapped[list[Series]] = relationship(back_populates="source")


class SourceRun(Base):
    __tablename__ = "source_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    pipeline_name: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    items_fetched: Mapped[int] = mapped_column(default=0)
    items_inserted: Mapped[int] = mapped_column(default=0)
    items_updated: Mapped[int] = mapped_column(default=0)
    items_failed: Mapped[int] = mapped_column(default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    source: Mapped[Source] = relationship(back_populates="runs")


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)


class Geography(Base):
    __tablename__ = "geographies"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    level: Mapped[str] = mapped_column(String(30), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("geographies.id"), nullable=True)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_dataset_source_external"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    geography_scope: Mapped[str | None] = mapped_column(String(100), nullable=True)
    update_frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    source: Mapped[Source] = relationship(back_populates="datasets")
    resources: Mapped[list[DatasetResource]] = relationship(back_populates="dataset")
    series: Mapped[list[Series]] = relationship(back_populates="dataset")


class DatasetResource(Base):
    __tablename__ = "dataset_resources"
    __table_args__ = (UniqueConstraint("dataset_id", "external_id", name="uq_resource_dataset_external"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    format: Mapped[str | None] = mapped_column(String(50), nullable=True)
    download_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    dataset: Mapped[Dataset] = relationship(back_populates="resources")


class Series(Base):
    __tablename__ = "series"
    __table_args__ = (UniqueConstraint("source_id", "external_code", name="uq_series_source_external"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id"), nullable=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    external_code: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    geography_id: Mapped[int | None] = mapped_column(ForeignKey("geographies.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    dataset: Mapped[Dataset | None] = relationship(back_populates="series")
    source: Mapped[Source] = relationship(back_populates="series")
    observations: Mapped[list[SeriesObservation]] = relationship(back_populates="series")


class SeriesObservation(Base):
    __tablename__ = "series_observations"
    __table_args__ = (
        UniqueConstraint("series_id", "obs_date", "revision_date", name="uq_series_observation_version"),
        Index("ix_obs_series_date", "series_id", "obs_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True)
    obs_date: Mapped[date] = mapped_column(Date, index=True)
    obs_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    obs_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    raw_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    series: Mapped[Series] = relationship(back_populates="observations")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(255), index=True)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), default="ES")
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_listed: Mapped[bool] = mapped_column(Boolean, default=False)
    source_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)

    aliases: Mapped[list[CompanyAlias]] = relationship(back_populates="company")
    identifiers: Mapped[list[CompanyIdentifier]] = relationship(back_populates="company")
    snapshots: Mapped[list[CompanySnapshot]] = relationship(back_populates="company")
    filings: Mapped[list[Filing]] = relationship(back_populates="company")


class CompanyAlias(Base):
    __tablename__ = "company_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    alias: Mapped[str] = mapped_column(String(255), index=True)

    company: Mapped[Company] = relationship(back_populates="aliases")


class CompanyIdentifier(Base):
    __tablename__ = "company_identifiers"
    __table_args__ = (
        UniqueConstraint("identifier_type", "identifier_value", name="uq_identifier_unique"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    identifier_type: Mapped[str] = mapped_column(String(50), index=True)
    identifier_value: Mapped[str] = mapped_column(String(255), index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)

    company: Mapped[Company] = relationship(back_populates="identifiers")


class CompanySnapshot(Base):
    __tablename__ = "company_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    legal_form: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cnae: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nace: Mapped[str | None] = mapped_column(String(50), nullable=True)
    province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    administrators_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    raw_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    company: Mapped[Company] = relationship(back_populates="snapshots")


class Filing(Base):
    __tablename__ = "filings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    filing_type: Mapped[str] = mapped_column(String(100), index=True)
    filing_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    company: Mapped[Company] = relationship(back_populates="filings")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ArticleChartSpec(Base):
    __tablename__ = "article_chart_specs"

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int | None] = mapped_column(ForeignKey("articles.id"), nullable=True, index=True)
    series_id: Mapped[int | None] = mapped_column(ForeignKey("series.id"), nullable=True, index=True)
    chart_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    spec_json: Mapped[dict[str, Any]] = mapped_column(JSON)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    label: Mapped[str] = mapped_column(String(100))
