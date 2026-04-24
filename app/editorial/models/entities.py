from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StoryCandidate(Base):
    __tablename__ = "story_candidates"
    __table_args__ = (
        UniqueConstraint("dedupe_hash", name="uq_story_candidate_dedupe_hash"),
        Index("ix_story_candidates_status_score", "status", "score_total"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    insight: Mapped[str] = mapped_column(Text)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    geography: Mapped[str | None] = mapped_column(String(100), nullable=True)
    period_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    suggested_chart_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    chart_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    chart_spec_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)
    dedupe_hash: Mapped[str] = mapped_column(String(255), index=True)
    score_total: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    @property
    def chart_type_suggested(self) -> str | None:
        # Backward-compatible alias used by editorial policy docs.
        return self.suggested_chart_type

    @chart_type_suggested.setter
    def chart_type_suggested(self, value: str | None) -> None:
        self.suggested_chart_type = value

    @property
    def effective_chart_rationale(self) -> str | None:
        if self.chart_rationale and str(self.chart_rationale).strip():
            return str(self.chart_rationale).strip()
        spec = self.chart_spec_json or {}
        raw = spec.get("chart_rationale")
        return str(raw).strip() if raw else None


class CandidateSignal(Base):
    __tablename__ = "candidate_signals"
    __table_args__ = (
        Index("ix_candidate_signals_signal_type", "signal_type"),
        UniqueConstraint("candidate_id", "signal_key", name="uq_candidate_signal_candidate_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("story_candidates.id"), index=True)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("signal_rules.id"), nullable=True, index=True)
    signal_type: Mapped[str] = mapped_column(String(80))
    signal_key: Mapped[str] = mapped_column(String(255), index=True)
    explanation: Mapped[str] = mapped_column(Text)
    strength: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class CandidateScore(Base):
    __tablename__ = "candidate_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("story_candidates.id"), unique=True, index=True)
    novelty_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    magnitude_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    freshness_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    editorial_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    clarity_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    robustness_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    noise_penalty: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    total_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class CandidateRelatedSeries(Base):
    __tablename__ = "candidate_related_series"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("story_candidates.id"), index=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(50), default="primary")


class CandidateRelatedCompany(Base):
    __tablename__ = "candidate_related_companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("story_candidates.id"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(50), default="mentioned")


class CandidateCross(Base):
    __tablename__ = "candidate_crosses"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("story_candidates.id"), index=True)
    left_entity: Mapped[str] = mapped_column(String(255))
    right_entity: Mapped[str] = mapped_column(String(255))
    rationale: Mapped[str] = mapped_column(Text)
    suggested_angle: Mapped[str] = mapped_column(Text)
    suggested_chart_type: Mapped[str | None] = mapped_column(String(50), nullable=True)


class CandidateDraft(Base):
    __tablename__ = "candidate_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("story_candidates.id"), unique=True, index=True)
    lead_neutral: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_paragraph: Mapped[str | None] = mapped_column(Text, nullable=True)
    analytical_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    alt_headlines_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    followup_questions_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    warnings_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EditorialReview(Base):
    __tablename__ = "editorial_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("story_candidates.id"), index=True)
    action: Mapped[str] = mapped_column(String(50), index=True)
    reviewer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class PublicationTarget(Base):
    __tablename__ = "publication_targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    adapter_type: Mapped[str] = mapped_column(String(50))
    config_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)


class PublishedStory(Base):
    __tablename__ = "published_stories"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_published_stories_slug"),
        Index("ix_published_stories_topic_published_at", "topic", "published_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("story_candidates.id"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("publication_targets.id"), index=True)
    slug: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    subtitle: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    chart_spec: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    sources: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="queued")
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class PublicStory(Base):
    """Historia publicada consumible por la fachada web (separada de `published_stories` / adaptadores CMS)."""

    __tablename__ = "public_stories"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_public_stories_slug"),
        UniqueConstraint("candidate_id", name="uq_public_stories_candidate_id"),
        Index("ix_public_stories_status_published_at", "status", "published_at"),
        Index("ix_public_stories_topic", "topic"),
        CheckConstraint(
            "(status != 'published') OR (published_at IS NOT NULL)",
            name="ck_public_stories_published_requires_date",
        ),
        CheckConstraint(
            "(status != 'scheduled') OR (scheduled_at IS NOT NULL)",
            name="ck_public_stories_scheduled_requires_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(Text, nullable=True)
    dek: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    topic: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    primary_chart_spec: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    secondary_chart_spec: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    chart_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("story_candidates.id"), nullable=False, index=True)
    sources: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    narrative_context_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="es")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class SignalRule(Base):
    __tablename__ = "signal_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    signal_type: Mapped[str] = mapped_column(String(80), index=True)
    params_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    weight: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=1)
    enabled: Mapped[bool] = mapped_column(default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class SignalRuleRevision(Base):
    __tablename__ = "signal_rule_revisions"
    __table_args__ = (Index("ix_signal_rule_revisions_rule_id", "rule_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("signal_rules.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(30))
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class SignalRuleImpactPreview(Base):
    __tablename__ = "signal_rule_impact_previews"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("signal_rules.id"), index=True)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    limit_series: Mapped[int] = mapped_column(default=200)
    override_params_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class SignalRuleImpactEvaluation(Base):
    __tablename__ = "signal_rule_impact_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    preview_id: Mapped[int] = mapped_column(ForeignKey("signal_rule_impact_previews.id"), index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("signal_rules.id"), index=True)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    predicted_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    actual_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
