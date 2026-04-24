from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CandidateOut(ORMModel):
    id: int
    title: str
    insight: str
    executive_summary: str | None
    why_it_matters: str | None
    geography: str | None
    period_label: str | None
    status: str
    score_total: Decimal | None
    dedupe_hash: str
    created_at: datetime
    suggested_chart_type: str | None = None
    chart_rationale: str | None = None
    chart_spec_json: dict[str, Any] | None = None

    @computed_field
    @property
    def chart_type_suggested(self) -> str | None:
        return self.suggested_chart_type


class SignalOut(ORMModel):
    id: int
    candidate_id: int
    rule_id: int | None
    signal_type: str
    signal_key: str
    explanation: str
    strength: Decimal
    payload_json: dict[str, Any] | None
    created_at: datetime


class ScoreOut(ORMModel):
    candidate_id: int
    novelty_score: Decimal
    magnitude_score: Decimal
    freshness_score: Decimal
    editorial_score: Decimal
    clarity_score: Decimal
    robustness_score: Decimal
    noise_penalty: Decimal
    total_score: Decimal
    rationale: str | None


class DraftOut(ORMModel):
    candidate_id: int
    lead_neutral: str | None
    base_paragraph: str | None
    analytical_version: str | None
    short_version: str | None
    alt_headlines_json: list[str] | None
    followup_questions_json: list[str] | None
    warnings_json: list[str] | None


class SignalRuleOut(ORMModel):
    id: int
    slug: str
    name: str
    signal_type: str
    params_json: dict[str, Any] | None
    weight: Decimal
    enabled: bool
    description: str | None


class SignalRuleUpsert(BaseModel):
    slug: str
    name: str
    signal_type: str
    params_json: dict[str, Any] | None = None
    weight: Decimal = Decimal("1")
    enabled: bool = True
    description: str | None = None


class SignalRuleRevisionOut(ORMModel):
    id: int
    rule_id: int | None
    action: str
    actor: str | None
    snapshot_json: dict[str, Any]
    created_at: datetime


class SignalRuleImpactPreviewOut(ORMModel):
    id: int
    rule_id: int
    actor: str | None
    limit_series: int
    override_params_json: dict[str, Any] | None
    result_json: dict[str, Any]
    created_at: datetime


class SignalRuleImpactEvaluationOut(ORMModel):
    id: int
    preview_id: int
    rule_id: int
    actor: str | None
    predicted_json: dict[str, Any]
    actual_json: dict[str, Any]
    metrics_json: dict[str, Any]
    created_at: datetime


class PublishedStoryOut(ORMModel):
    id: int
    candidate_id: int
    target_id: int
    slug: str | None
    title: str | None
    subtitle: str | None
    body: str | None
    chart_spec: dict[str, Any] | None
    topic: str | None
    tags: list[str] | None
    sources: list[dict[str, Any]] | None
    external_id: str | None
    url: str | None
    status: str
    payload_json: dict[str, Any] | None
    published_at: datetime | None
    updated_at: datetime


class SimulateSignalsRequest(BaseModel):
    overrides: dict[str, dict[str, Any]] | None = Field(
        default=None,
        description="Overrides por signal_type para simular reglas sin persistir cambios.",
        examples=[{"strong_period_change": {"mom_threshold_pct": 12}}],
    )


class SimulatedSignalOut(BaseModel):
    signal_type: str
    signal_key: str
    explanation: str
    strength: str
    period_label: str


class SimulateSignalsResponse(BaseModel):
    series_id: int
    signals_count: int
    signals: list[SimulatedSignalOut]


class ImpactPreviewRequest(BaseModel):
    override_params: dict[str, Any] | None = Field(
        default=None,
        description="Parámetros a sobreescribir para la regla evaluada.",
        examples=[{"mom_threshold_pct": 12}],
    )


class ImpactPreviewCounts(BaseModel):
    signals_count: int
    candidate_count: int


class ImpactPreviewDelta(BaseModel):
    signals_added: int
    signals_removed: int
    candidates_delta: int


class ImpactPreviewExamples(BaseModel):
    added_signal_keys: list[str]
    removed_signal_keys: list[str]
    kept_signal_keys: list[str]


class ImpactPreviewResponse(BaseModel):
    rule_id: int
    signal_type: str
    limit_series: int
    baseline: ImpactPreviewCounts
    simulated: ImpactPreviewCounts
    delta: ImpactPreviewDelta
    examples: ImpactPreviewExamples
    impact_score: str
    override_params: dict[str, Any]
    preview_id: int | None = None


class RuleDeleteResponse(BaseModel):
    deleted: bool
    rule_id: int


class RuleRecomputeResponse(BaseModel):
    rule_id: int
    signal_type: str
    matched_signals: int
    signals_detected: int
    signals_written: int
    created: int
    updated: int


class RuleRevisionDiffResponse(BaseModel):
    rule_id: int
    revision_a_id: int
    revision_b_id: int
    revision_a_action: str
    revision_b_action: str
    changed_fields: dict[str, dict[str, Any]]
    params_diff: dict[str, dict[str, Any]]
    total_changes: int
    change_magnitude_score: str


class RuleTimelineChangeSummary(BaseModel):
    changed_fields: dict[str, dict[str, Any]]
    params_diff: dict[str, dict[str, Any]]
    critical_keys: list[str] = []
    is_critical: bool


class RuleTimelineItem(BaseModel):
    revision_id: int
    action: str
    actor: str | None
    created_at: datetime
    change_summary: RuleTimelineChangeSummary
    snapshot: dict[str, Any]


class RuleTimelineResponse(BaseModel):
    rule_id: int
    rule_slug: str
    total_revisions: int
    critical_events: int
    timeline: list[RuleTimelineItem]


class RuleAccuracyLeaderboardItem(BaseModel):
    rule_id: int
    rule_slug: str
    signal_type: str
    evaluations_count: int
    mae_signal: float | None
    mae_candidate: float | None
    mape_signal: float | None
    mape_candidate: float | None
    combined_error_score: float
    stability_label: str


class RuleAccuracyLeaderboardResponse(BaseModel):
    items: list[RuleAccuracyLeaderboardItem]


class RuleAccuracyRollingMetrics(BaseModel):
    mae_signal: float
    mae_candidate: float
    mape_signal: float
    mape_candidate: float


class RuleAccuracyTrendPoint(BaseModel):
    evaluation_id: int
    created_at: datetime
    rolling_metrics: RuleAccuracyRollingMetrics


class RuleAccuracyTrendResponse(BaseModel):
    rule_id: int
    rule_slug: str
    signal_type: str
    window_size: int
    points: list[RuleAccuracyTrendPoint]
    latest_rolling_metrics: RuleAccuracyRollingMetrics | None


class RuleAccuracyAlertItem(BaseModel):
    rule_id: int
    rule_slug: str
    signal_type: str
    evaluations_count: int
    combined_error_score: float
    severity: str


class RuleAccuracyAlertsResponse(BaseModel):
    items: list[RuleAccuracyAlertItem]


class CandidateCrossOut(BaseModel):
    left_entity: str
    right_entity: str
    rationale: str
    suggested_angle: str
    suggested_chart_type: str | None = None


class CandidateCrossesResponse(BaseModel):
    candidate_id: int
    crosses: list[CandidateCrossOut]


class SendToCmsResponse(BaseModel):
    published_story_id: int
    status: str
    target_id: int


class DashboardOverviewResponse(BaseModel):
    candidates_total: int
    candidates_new: int
    candidates_reviewing: int
    candidates_shortlisted: int
    candidates_published: int
    signals_total: int


class DashboardRecentCandidate(BaseModel):
    id: int
    title: str
    status: str
    score_total: float | None
    created_at: datetime


class DashboardFullResponse(BaseModel):
    overview: DashboardOverviewResponse
    accuracy_leaderboard: list[RuleAccuracyLeaderboardItem]
    rule_alerts: list[RuleAccuracyAlertItem]
    recent_candidates: list[DashboardRecentCandidate]
