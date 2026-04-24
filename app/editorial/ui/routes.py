from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.auth import ROLE_RANK, AuthContext, require_role
from app.db.session import get_db
from app.editorial.models import (
    CandidateCross,
    CandidateDraft,
    CandidateRelatedSeries,
    CandidateScore,
    CandidateSignal,
    EditorialReview,
    PublicationTarget,
    PublishedStory,
    PublicStory,
    SignalRule,
    StoryCandidate,
)
from app.editorial.schemas.public_api import PublishCandidatePayload
from app.editorial.services.candidate_service import run_signal_pipeline
from app.editorial.services.public_story_service import publish_candidate
from app.editorial.services.publication_service import send_to_publication_target
from app.editorial.services.review_service import set_candidate_state
from app.editorial.services.signal_detector import simulate_signals_for_series
from app.models.entities import Series, SeriesObservation, Source, SourceRun

ROOT_DIR = Path(__file__).resolve().parents[3]
templates = Jinja2Templates(directory=str(ROOT_DIR / "templates"))
router = APIRouter(prefix="/editorial/ui", tags=["editorial-ui"])
DB_SESSION = Depends(get_db)
VIEWER_AUTH = require_role("viewer")
EDITOR_AUTH = require_role("editor")


def _fmt_decimal(value: object | None) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_datetime(value: object | None) -> str:
    if not isinstance(value, datetime):
        return "-"
    return value.strftime("%Y-%m-%d %H:%M")


templates.env.filters["fmt_decimal"] = _fmt_decimal
templates.env.filters["fmt_datetime"] = _fmt_datetime


def _parse_scheduled_at_form(raw: str | None) -> datetime | None:
    if raw is None or not str(raw).strip():
        return None
    s = str(raw).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _publish_form_defaults_from_state(
    candidate: StoryCandidate,
    draft: CandidateDraft | None,
    public_story: PublicStory | None,
) -> dict[str, str]:
    if public_story is not None:
        tags_csv = ", ".join(public_story.tags or [])
        return {
            "title": public_story.title,
            "subtitle": public_story.subtitle or "",
            "dek": public_story.dek or "",
            "body_markdown": public_story.body_markdown or "",
            "topic": public_story.topic or "",
            "tags_csv": tags_csv,
            "summary": public_story.summary or "",
            "slug": public_story.slug,
            "public_status": public_story.status,
            "public_slug": public_story.slug,
            "public_story_id": str(public_story.id),
        }
    title = (candidate.title or "").strip() or f"Candidato {candidate.id}"
    subtitle = (candidate.executive_summary or "").strip()
    if len(subtitle) > 2000:
        subtitle = subtitle[:2000]
    dek = (candidate.why_it_matters or "").strip()
    if len(dek) > 500:
        dek = dek[:500]
    parts: list[str] = []
    if draft:
        for bit in (draft.lead_neutral, draft.base_paragraph):
            if bit and str(bit).strip():
                parts.append(str(bit).strip())
        if draft.analytical_version and str(draft.analytical_version).strip():
            parts.append("## Análisis\n\n" + str(draft.analytical_version).strip())
    body = "\n\n".join(parts) if parts else ""
    if not body.strip():
        insight = (candidate.insight or "").strip()
        body = f"## Insight\n\n{insight}" if insight else "## Borrador\n\n_(Completa el cuerpo en Markdown antes de publicar.)_"
    return {
        "title": title,
        "subtitle": subtitle,
        "dek": dek,
        "body_markdown": body,
        "topic": "",
        "tags_csv": "",
        "summary": "",
        "slug": "",
        "public_status": "",
        "public_slug": "",
        "public_story_id": "",
    }


def _series_points(db: Session, series_id: int, limit: int = 60) -> list[SeriesObservation]:
    return list(
        db.scalars(
            select(SeriesObservation)
            .where(SeriesObservation.series_id == series_id)
            .order_by(SeriesObservation.obs_date.desc())
            .limit(limit)
        ).all()
    )[::-1]


def _signal_sparkline_bundle(db: Session, signal: CandidateSignal) -> dict[str, object]:
    """Sparkline payload for a signal (lazy-load friendly)."""
    raw_series_id = (signal.payload_json or {}).get("series_id")
    if raw_series_id is None:
        return {"state": "na", "series_label": None, "payload": None}
    series_id = int(raw_series_id)
    series_row = db.scalar(select(Series).where(Series.id == series_id))
    series_label = (
        f"{series_row.external_code} - {series_row.name}" if series_row is not None else None
    )
    points = _series_points(db, series_id, limit=24)
    compact_labels = [item.obs_date.isoformat() for item in points]
    compact_values = [float(item.obs_value) if item.obs_value is not None else None for item in points]
    non_null_points = [value for value in compact_values if value is not None]
    if len(non_null_points) < 2:
        return {"state": "insufficient", "series_label": series_label, "payload": None}
    return {
        "state": "ok",
        "series_label": series_label,
        "payload": {"labels": compact_labels, "values": compact_values},
    }


def _build_candidate_chart_data(
    primary_series: Series | None,
    primary_points: list[SeriesObservation],
    secondary_series: Series | None = None,
    secondary_points: list[SeriesObservation] | None = None,
    *,
    include_comparison: bool = False,
) -> dict[str, object] | None:
    if primary_series is None or len(primary_points) < 1:
        return None

    primary_by_day = {
        obs.obs_date.isoformat(): float(obs.obs_value)
        for obs in primary_points
        if obs.obs_value is not None
    }
    labels = sorted(primary_by_day.keys())
    if not labels:
        return None

    datasets: list[dict[str, object]] = [
        {
            "label": (
                f"{primary_series.name} ({primary_series.unit})"
                if primary_series.unit
                else primary_series.name
            ),
            "data": [primary_by_day.get(day) for day in labels],
            "borderColor": "#2563eb",
            "backgroundColor": "#2563eb",
        }
    ]
    meta: dict[str, object] = {
        "series_name": primary_series.name,
        "series_code": primary_series.external_code,
        "unit": primary_series.unit,
        "source": primary_series.source.name if primary_series.source else None,
        "frequency": primary_series.frequency,
    }

    if (
        include_comparison
        and secondary_series is not None
        and secondary_points
        and len(secondary_points) >= 2
    ):
        secondary_by_day = {
            obs.obs_date.isoformat(): float(obs.obs_value)
            for obs in secondary_points
            if obs.obs_value is not None
        }
        common_labels = sorted(set(labels).intersection(secondary_by_day.keys()))
        if len(common_labels) >= 2:
            labels = common_labels
            datasets[0]["data"] = [primary_by_day.get(day) for day in labels]
            datasets.append(
                {
                    "label": (
                        f"{secondary_series.name} ({secondary_series.unit})"
                        if secondary_series.unit
                        else secondary_series.name
                    ),
                    "data": [secondary_by_day.get(day) for day in labels],
                    "borderColor": "#dc2626",
                    "backgroundColor": "#dc2626",
                }
            )
            meta["comparison_series"] = {
                "series_name": secondary_series.name,
                "series_code": secondary_series.external_code,
                "unit": secondary_series.unit,
                "source": secondary_series.source.name if secondary_series.source else None,
                "frequency": secondary_series.frequency,
            }
    return {"labels": labels, "datasets": datasets, "meta": meta}


def _daily_candidate_chart(
    db: Session,
    days: int = 14,
    bucket: str = "day",
) -> dict[str, object]:
    today = datetime.now(UTC).date()
    day_labels = [
        (today - timedelta(days=offset)).isoformat()
        for offset in range(days - 1, -1, -1)
    ]
    new_counts = defaultdict(int)
    accepted_counts = defaultdict(int)
    discarded_counts = defaultdict(int)

    new_rows = db.scalars(
        select(StoryCandidate).where(
            StoryCandidate.created_at
            >= datetime.combine(today - timedelta(days=days - 1), time.min)
        )
    ).all()
    for row in new_rows:
        new_counts[row.created_at.date().isoformat()] += 1

    review_rows = db.scalars(
        select(EditorialReview).where(
            EditorialReview.created_at
            >= datetime.combine(today - timedelta(days=days - 1), time.min),
            EditorialReview.action.in_(["accepted", "discarded"]),
        )
    ).all()
    for row in review_rows:
        key = row.created_at.date().isoformat()
        if row.action == "accepted":
            accepted_counts[key] += 1
        if row.action == "discarded":
            discarded_counts[key] += 1

    if bucket == "week":
        weekly_new: dict[str, int] = defaultdict(int)
        weekly_accepted: dict[str, int] = defaultdict(int)
        weekly_discarded: dict[str, int] = defaultdict(int)
        for day in day_labels:
            dt = date.fromisoformat(day)
            iso_year, iso_week, _ = dt.isocalendar()
            week_key = f"{iso_year}-W{iso_week:02d}"
            weekly_new[week_key] += new_counts.get(day, 0)
            weekly_accepted[week_key] += accepted_counts.get(day, 0)
            weekly_discarded[week_key] += discarded_counts.get(day, 0)

        week_labels = sorted(set(weekly_new) | set(weekly_accepted) | set(weekly_discarded))
        return {
            "labels": week_labels,
            "datasets": [
                {"label": "Nuevos", "data": [weekly_new.get(label, 0) for label in week_labels]},
                {
                    "label": "Aceptados",
                    "data": [weekly_accepted.get(label, 0) for label in week_labels],
                },
                {
                    "label": "Descartados",
                    "data": [weekly_discarded.get(label, 0) for label in week_labels],
                },
            ],
        }

    return {
        "labels": day_labels,
        "datasets": [
            {"label": "Nuevos", "data": [new_counts.get(day, 0) for day in day_labels]},
            {"label": "Aceptados", "data": [accepted_counts.get(day, 0) for day in day_labels]},
            {"label": "Descartados", "data": [discarded_counts.get(day, 0) for day in day_labels]},
        ],
    }


def _rule_performance_chart(db: Session) -> dict[str, object] | None:
    rules = list(db.scalars(select(SignalRule).order_by(SignalRule.id.asc())).all())
    if not rules:
        return None

    generated_by_rule: dict[int, set[int]] = defaultdict(set)
    for signal in db.scalars(
        select(CandidateSignal).where(CandidateSignal.rule_id.is_not(None))
    ).all():
        if signal.rule_id is not None:
            generated_by_rule[int(signal.rule_id)].add(signal.candidate_id)

    accepted_candidate_ids = {
        row.candidate_id
        for row in db.scalars(
            select(EditorialReview).where(EditorialReview.action == "accepted")
        ).all()
    }
    approved_by_rule: dict[int, set[int]] = defaultdict(set)
    for signal in db.scalars(
        select(CandidateSignal).where(CandidateSignal.rule_id.is_not(None))
    ).all():
        if signal.rule_id is not None and signal.candidate_id in accepted_candidate_ids:
            approved_by_rule[int(signal.rule_id)].add(signal.candidate_id)

    labels = [rule.slug for rule in rules]
    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Generados",
                "data": [len(generated_by_rule.get(rule.id, set())) for rule in rules],
            },
            {
                "label": "Aprobados",
                "data": [len(approved_by_rule.get(rule.id, set())) for rule in rules],
            },
        ],
    }


def _status_distribution_chart(db: Session) -> dict[str, object]:
    labels = ["new", "reviewing", "shortlisted", "accepted", "discarded", "published", "archived"]
    values: list[int] = []
    for status in labels:
        count = db.scalar(
            select(func.count()).select_from(StoryCandidate).where(StoryCandidate.status == status)
        )
        values.append(int(count or 0))
    return {"labels": labels, "datasets": [{"label": "Candidates", "data": values}]}


def _dashboard_kpis(db: Session) -> dict[str, int]:
    now = datetime.now(UTC)
    since_7d = now - timedelta(days=7)
    since_30d = now - timedelta(days=30)

    new_7d = db.scalar(
        select(func.count()).select_from(StoryCandidate).where(StoryCandidate.created_at >= since_7d)
    )
    new_30d = db.scalar(
        select(func.count()).select_from(StoryCandidate).where(StoryCandidate.created_at >= since_30d)
    )
    accepted_total = db.scalar(
        select(func.count()).select_from(StoryCandidate).where(StoryCandidate.status == "accepted")
    )
    discarded_total = db.scalar(
        select(func.count()).select_from(StoryCandidate).where(StoryCandidate.status == "discarded")
    )
    return {
        "new_7d": int(new_7d or 0),
        "new_30d": int(new_30d or 0),
        "accepted_total": int(accepted_total or 0),
        "discarded_total": int(discarded_total or 0),
    }


def _scheduler_runs_snapshot(db: Session) -> list[dict[str, object]]:
    tracked_jobs = [
        "ingest_ine_series",
        "ingest_bde_series",
        "ingest_oecd_series",
        "detect_daily_signals",
        "refresh_scores",
        "detect_weekly_signals",
        "maintenance_dedupe_observations",
    ]
    rows = (
        db.query(SourceRun)
        .filter(SourceRun.pipeline_name.in_(tracked_jobs))
        .order_by(SourceRun.pipeline_name.asc(), SourceRun.started_at.desc())
        .all()
    )
    latest_by_job: dict[str, SourceRun] = {}
    for row in rows:
        if row.pipeline_name not in latest_by_job:
            latest_by_job[row.pipeline_name] = row
    status_to_class = {
        "success": "ok",
        "running": "running",
        "partial": "warn",
        "failed": "error",
    }
    return [
        {
            "pipeline_name": job,
            "last_status": latest_by_job[job].status if job in latest_by_job else "-",
            "status_class": status_to_class.get(
                (latest_by_job[job].status or "").lower() if job in latest_by_job else "",
                "neutral",
            ),
            "last_started_at": latest_by_job[job].started_at if job in latest_by_job else None,
            "last_finished_at": latest_by_job[job].finished_at if job in latest_by_job else None,
            "items_fetched": latest_by_job[job].items_fetched if job in latest_by_job else None,
            "items_inserted": latest_by_job[job].items_inserted if job in latest_by_job else None,
            "items_failed": latest_by_job[job].items_failed if job in latest_by_job else None,
        }
        for job in tracked_jobs
    ]


def _rule_breakdown_chart(db: Session) -> dict[str, object] | None:
    rules = list(db.scalars(select(SignalRule).order_by(SignalRule.slug.asc())).all())
    if not rules:
        return None

    generated_by_rule: dict[int, set[int]] = defaultdict(set)
    for signal in db.scalars(
        select(CandidateSignal).where(CandidateSignal.rule_id.is_not(None))
    ).all():
        if signal.rule_id is not None:
            generated_by_rule[int(signal.rule_id)].add(signal.candidate_id)

    accepted_candidates = {
        row.candidate_id
        for row in db.scalars(
            select(EditorialReview).where(EditorialReview.action == "accepted")
        ).all()
    }
    discarded_candidates = {
        row.candidate_id
        for row in db.scalars(
            select(EditorialReview).where(EditorialReview.action == "discarded")
        ).all()
    }

    generated_values: list[int] = []
    accepted_values: list[int] = []
    discarded_values: list[int] = []
    acceptance_ratio_values: list[float] = []
    labels: list[str] = []
    for rule in rules:
        candidate_ids = generated_by_rule.get(rule.id, set())
        generated = len(candidate_ids)
        accepted = len(candidate_ids.intersection(accepted_candidates))
        discarded = len(candidate_ids.intersection(discarded_candidates))
        ratio = round((accepted / generated) * 100, 1) if generated > 0 else 0.0
        labels.append(rule.slug)
        generated_values.append(generated)
        accepted_values.append(accepted)
        discarded_values.append(discarded)
        acceptance_ratio_values.append(ratio)

    return {
        "labels": labels,
        "datasets": [
            {"label": "Generados", "data": generated_values, "backgroundColor": "#2563eb"},
            {"label": "Aceptados", "data": accepted_values, "backgroundColor": "#059669"},
            {"label": "Descartados", "data": discarded_values, "backgroundColor": "#dc2626"},
        ],
        "acceptance_ratio": acceptance_ratio_values,
    }


def _source_breakdown_chart(db: Session, limit_sources: int = 12) -> dict[str, object] | None:
    source_pairs = list(
        db.execute(
            select(
                CandidateRelatedSeries.candidate_id,
                Source.slug,
            )
            .join(Series, Series.id == CandidateRelatedSeries.series_id)
            .join(Source, Source.id == Series.source_id)
            .distinct(CandidateRelatedSeries.candidate_id, Source.slug)
        ).all()
    )
    if not source_pairs:
        return None

    totals_by_source: dict[str, int] = defaultdict(int)
    for _, source_slug in source_pairs:
        totals_by_source[source_slug] += 1

    top_sources = sorted(totals_by_source.items(), key=lambda item: item[1], reverse=True)[:limit_sources]
    labels = [slug.upper() for slug, _ in top_sources]
    values = [count for _, count in top_sources]
    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Candidates por fuente",
                "data": values,
                "backgroundColor": "#7c3aed",
            }
        ],
    }


def _audit_base_candidates(db: Session, days: int, *, max_rows: int = 2000) -> list[StoryCandidate]:
    since_dt = datetime.now(UTC) - timedelta(days=days)
    return list(
        db.scalars(
            select(StoryCandidate)
            .where(StoryCandidate.created_at >= since_dt)
            .order_by(StoryCandidate.created_at.desc())
            .limit(max_rows)
        ).all()
    )


def _audit_filter_options(candidates: list[StoryCandidate]) -> tuple[list[str], list[str]]:
    types: set[str] = set()
    policies: set[str] = set()
    for candidate in candidates:
        ct = candidate.chart_type_suggested
        types.add(ct if ct else "__unset__")
        spec = candidate.chart_spec_json or {}
        pol = spec.get("chart_policy")
        policies.add(str(pol) if pol else "__unset__")
    return sorted(types, key=lambda x: (x == "__unset__", x)), sorted(policies, key=lambda x: (x == "__unset__", x))


def _audit_apply_filters(
    candidates: list[StoryCandidate],
    *,
    chart_type: str | None,
    chart_policy: str | None,
) -> list[StoryCandidate]:
    out: list[StoryCandidate] = []
    for candidate in candidates:
        if chart_type:
            current = candidate.chart_type_suggested or "__unset__"
            if current != chart_type:
                continue
        if chart_policy:
            spec = candidate.chart_spec_json or {}
            pol = str(spec.get("chart_policy") or "") or "__unset__"
            if pol != chart_policy:
                continue
        out.append(candidate)
    return out


def _chart_policy_summary_for_candidates(db: Session, candidates: list[StoryCandidate]) -> dict[str, object]:
    type_counts: dict[str, int] = defaultdict(int)
    policy_counts: dict[str, int] = defaultdict(int)
    rationale_counts: dict[str, int] = defaultdict(int)
    fallback_hits = 0
    missing_rationale = 0
    total = len(candidates)

    for candidate in candidates:
        chart_type = candidate.chart_type_suggested or "unset"
        type_counts[chart_type] += 1
        spec = candidate.chart_spec_json or {}
        policy = str(spec.get("chart_policy") or "unset")
        policy_counts[policy] += 1

        rationale = candidate.effective_chart_rationale or ""
        if not rationale:
            missing_rationale += 1
        else:
            rationale_counts[rationale] += 1
            if "fallback" in rationale.lower():
                fallback_hits += 1

    type_labels = sorted(type_counts.keys())
    policy_labels = sorted(policy_counts.keys())

    top_rationales = sorted(rationale_counts.items(), key=lambda item: item[1], reverse=True)[:8]
    top_rules: list[tuple[str, int]] = []
    candidate_ids = [c.id for c in candidates]
    if candidate_ids:
        rule_rows = list(
            db.execute(
                select(SignalRule.slug, func.count())
                .select_from(CandidateSignal)
                .join(SignalRule, SignalRule.id == CandidateSignal.rule_id)
                .where(CandidateSignal.candidate_id.in_(candidate_ids))
                .where(CandidateSignal.rule_id.is_not(None))
                .group_by(SignalRule.slug)
                .order_by(func.count().desc())
                .limit(8)
            ).all()
        )
        top_rules = [(str(slug), int(cnt or 0)) for slug, cnt in rule_rows]

    fallback_pct = round((fallback_hits / total) * 100, 1) if total else 0.0
    no_rationale_pct = round((missing_rationale / total) * 100, 1) if total else 0.0

    if total == 0:
        quality_health = "unknown"
    elif fallback_pct < 15 and no_rationale_pct < 10:
        quality_health = "ok"
    elif fallback_pct < 35 and no_rationale_pct < 25:
        quality_health = "warn"
    else:
        quality_health = "bad"

    return {
        "recent_candidates": candidates,
        "type_chart": {
            "labels": type_labels,
            "datasets": [{"label": "Candidates", "data": [type_counts[label] for label in type_labels]}],
        }
        if type_labels
        else None,
        "policy_chart": {
            "labels": policy_labels,
            "datasets": [{"label": "Candidates", "data": [policy_counts[label] for label in policy_labels]}],
        }
        if policy_labels
        else None,
        "chart_quality": {
            "sample_size": total,
            "fallback_count": fallback_hits,
            "fallback_pct": fallback_pct,
            "no_rationale_count": missing_rationale,
            "no_rationale_pct": no_rationale_pct,
            "health": quality_health,
            "top_rationales": [{"text": text, "count": count} for text, count in top_rationales],
            "top_rules": [{"slug": slug, "count": count} for slug, count in top_rules],
        },
    }


def _chart_audit_filtered(
    db: Session,
    *,
    days: int,
    chart_type: str | None,
    chart_policy: str | None,
    table_limit: int = 500,
) -> dict[str, object]:
    base = _audit_base_candidates(db, days, max_rows=2000)
    type_options, policy_options = _audit_filter_options(base)
    filtered = _audit_apply_filters(base, chart_type=chart_type, chart_policy=chart_policy)
    summary = _chart_policy_summary_for_candidates(db, filtered)
    summary["recent_candidates"] = filtered[:table_limit]
    summary["chart_type_options"] = type_options
    summary["chart_policy_options"] = policy_options
    summary["filter_chart_type"] = chart_type or ""
    summary["filter_chart_policy"] = chart_policy or ""
    summary["filtered_total"] = len(filtered)
    summary["table_row_cap"] = table_limit
    return summary


@router.get("/", include_in_schema=False)
def ui_root() -> RedirectResponse:
    return RedirectResponse(url="/editorial/ui/queue", status_code=303)


@router.get("/dashboard")
def dashboard_view(
    request: Request,
    db: Session = DB_SESSION,
    _auth: AuthContext = VIEWER_AUTH,
    window_days: int = 90,
    bucket: str = "day",
):
    if window_days not in {7, 30, 90}:
        window_days = 90
    if bucket not in {"day", "week"}:
        bucket = "day"

    kpis = _dashboard_kpis(db)
    daily_chart = _daily_candidate_chart(db, days=window_days, bucket=bucket)
    rule_chart = _rule_breakdown_chart(db)
    source_chart = _source_breakdown_chart(db)
    return templates.TemplateResponse(
        request=request,
        name="editorial/dashboard.html",
        context={
            "title": "Editorial Dashboard",
            "kpis": kpis,
            "daily_chart": daily_chart,
            "rule_chart": rule_chart,
            "source_chart": source_chart,
            "status_chart": _status_distribution_chart(db),
            "scheduler_runs": _scheduler_runs_snapshot(db),
            "window_days": window_days,
            "bucket": bucket,
        },
    )


@router.get("/dashboard/scheduler-runs", response_class=HTMLResponse)
def dashboard_scheduler_runs_partial(
    request: Request,
    db: Session = DB_SESSION,
    _auth: AuthContext = VIEWER_AUTH,
):
    return templates.TemplateResponse(
        request=request,
        name="editorial/partials/scheduler_runs_table.html",
        context={"scheduler_runs": _scheduler_runs_snapshot(db)},
    )


@router.get("/queue")
def queue_view(
    request: Request,
    db: Session = DB_SESSION,
    _auth: AuthContext = VIEWER_AUTH,
    status: str | None = None,
    min_score: float | None = None,
    created_from: date | None = None,
    limit: int = 100,
    message: str | None = None,
    error: str | None = None,
):
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500
    stmt = select(StoryCandidate).order_by(StoryCandidate.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(StoryCandidate.status == status)
    if min_score is not None:
        stmt = stmt.where(
            StoryCandidate.score_total.is_not(None),
            StoryCandidate.score_total >= min_score,
        )
    if created_from:
        created_from_dt = datetime.combine(created_from, time.min)
        stmt = stmt.where(StoryCandidate.created_at >= created_from_dt)

    candidates = list(db.scalars(stmt).all())
    candidate_ids = [item.id for item in candidates]

    series_rows: list[tuple[int, str, str]] = []
    if candidate_ids:
        series_rows = list(
            db.execute(
                select(CandidateRelatedSeries.candidate_id, Series.external_code, Series.name)
                .join(Series, Series.id == CandidateRelatedSeries.series_id)
                .where(CandidateRelatedSeries.candidate_id.in_(candidate_ids))
            ).all()
        )
    sources_by_candidate: dict[int, list[str]] = {}
    for candidate_id, external_code, name in series_rows:
        label = f"{external_code} - {name}"
        sources_by_candidate.setdefault(candidate_id, []).append(label)

    status_options = [
        row[0]
        for row in db.execute(
            select(StoryCandidate.status).distinct().order_by(StoryCandidate.status.asc())
        ).all()
        if row[0]
    ]

    return templates.TemplateResponse(
        request=request,
        name="editorial/queue.html",
        context={
            "title": "Editorial Queue",
            "candidates": candidates,
            "sources_by_candidate": sources_by_candidate,
            "filters": {
                "status": status,
                "min_score": min_score,
                "created_from": created_from.isoformat() if created_from else "",
                "limit": limit,
            },
            "status_options": status_options,
            "message": message,
            "error": error,
        },
    )


@router.post("/candidates/{candidate_id}/state")
def candidate_state_action(
    candidate_id: int,
    action: str = Form(...),
    from_view: str = Form(default="queue"),
    reviewer: str | None = Form(default=None),
    db: Session = DB_SESSION,
    _auth: AuthContext = EDITOR_AUTH,
):
    transition_map = {
        "shortlist": "shortlisted",
        "approve": "accepted",
        "discard": "discarded",
    }
    next_state = transition_map.get(action)
    if not next_state:
        return _redirect_with_notice(from_view, candidate_id, error="Accion no soportada")
    try:
        set_candidate_state(db, candidate_id, next_state, reviewer=reviewer)
        db.commit()
        return _redirect_with_notice(
            from_view,
            candidate_id,
            message=f"Candidate {candidate_id} actualizado a {next_state}",
        )
    except ValueError as exc:
        db.rollback()
        return _redirect_with_notice(from_view, candidate_id, error=str(exc))


@router.post("/candidates/{candidate_id}/send")
def candidate_send_action(
    candidate_id: int,
    target: str = Form(default="internal"),
    from_view: str = Form(default="detail"),
    db: Session = DB_SESSION,
    _auth: AuthContext = EDITOR_AUTH,
):
    try:
        row = send_to_publication_target(db, candidate_id, target)
        db.commit()
        return _redirect_with_notice(
            from_view,
            candidate_id,
            message=f"Candidate {candidate_id} enviado ({row.status}) a target {target}",
        )
    except ValueError as exc:
        db.rollback()
        return _redirect_with_notice(from_view, candidate_id, error=str(exc))


@router.post("/candidates/{candidate_id}/publish-web")
def candidate_publish_web_action(
    candidate_id: int,
    from_view: str = Form(default="detail"),
    reviewer: str | None = Form(default=None),
    title: str = Form(...),
    subtitle: str = Form(default=""),
    dek: str = Form(default=""),
    body_markdown: str = Form(...),
    topic: str = Form(default=""),
    tags_csv: str = Form(default=""),
    summary: str = Form(default=""),
    slug: str = Form(default=""),
    scheduled_at: str | None = Form(default=None),
    save_as_draft: str | None = Form(default=None),
    db: Session = DB_SESSION,
    _auth: AuthContext = EDITOR_AUTH,
):
    actor = (reviewer or "").strip() or (_auth.api_key[:48] if _auth.api_key else None)
    tags_list = [t.strip().lower() for t in (tags_csv or "").split(",") if t.strip()] or None
    slug_val = (slug or "").strip() or None
    save_flag = save_as_draft in ("on", "true", "1", "yes")
    sched: datetime | None
    try:
        sched = _parse_scheduled_at_form(scheduled_at)
    except ValueError:
        return _redirect_with_notice(from_view, candidate_id, error="scheduled_at: formato de fecha inválido (usa ISO o datetime-local)")
    try:
        payload = PublishCandidatePayload(
            title=title.strip(),
            subtitle=(subtitle or "").strip() or None,
            dek=(dek or "").strip() or None,
            body_markdown=body_markdown,
            topic=(topic or "").strip() or None,
            tags=tags_list,
            summary=(summary or "").strip() or None,
            slug=slug_val,
            scheduled_at=sched,
            save_as_draft=save_flag,
        )
    except ValidationError as exc:
        parts = "; ".join(f"{list(e.get('loc', []))}: {e.get('msg')}" for e in exc.errors()[:4])
        return _redirect_with_notice(from_view, candidate_id, error=f"Validación: {parts}")
    try:
        row = publish_candidate(db, candidate_id, payload, actor=actor)
        db.commit()
    except ValueError as exc:
        db.rollback()
        return _redirect_with_notice(from_view, candidate_id, error=str(exc))
    verb = {"published": "publicada", "draft": "guardada como borrador", "scheduled": "programada"}.get(
        row.status, row.status
    )
    return _redirect_with_notice(
        from_view,
        candidate_id,
        message=f"Historia web ({verb}): slug «{row.slug}» · id {row.id} · estado {row.status}",
    )


@router.get("/candidates/{candidate_id}")
def candidate_detail_view(
    candidate_id: int,
    request: Request,
    db: Session = DB_SESSION,
    _auth: AuthContext = VIEWER_AUTH,
    message: str | None = None,
    error: str | None = None,
):
    candidate = db.get(StoryCandidate, candidate_id)
    if candidate is None:
        return _redirect_with_notice("queue", candidate_id, error="Candidate no encontrado")

    signals = list(
        db.scalars(
            select(CandidateSignal)
            .where(CandidateSignal.candidate_id == candidate_id)
            .order_by(CandidateSignal.created_at.desc())
        ).all()
    )
    score = db.scalar(select(CandidateScore).where(CandidateScore.candidate_id == candidate_id))
    crosses = list(
        db.scalars(
            select(CandidateCross)
            .where(CandidateCross.candidate_id == candidate_id)
            .order_by(CandidateCross.id.desc())
        ).all()
    )
    draft = db.scalar(select(CandidateDraft).where(CandidateDraft.candidate_id == candidate_id))
    reviews = list(
        db.scalars(
            select(EditorialReview)
            .where(EditorialReview.candidate_id == candidate_id)
            .order_by(EditorialReview.created_at.desc())
        ).all()
    )
    related_series_rows = list(
        db.execute(
            select(
                CandidateRelatedSeries.series_id,
                CandidateRelatedSeries.relation_type,
                Series.external_code,
                Series.name,
            )
            .join(Series, Series.id == CandidateRelatedSeries.series_id)
            .where(CandidateRelatedSeries.candidate_id == candidate_id)
            .order_by(
                case((CandidateRelatedSeries.relation_type == "primary", 0), else_=1),
                CandidateRelatedSeries.id.asc(),
            )
        ).all()
    )
    linked_series = list(
        db.scalars(
            select(Series)
            .join(CandidateRelatedSeries, CandidateRelatedSeries.series_id == Series.id)
            .where(CandidateRelatedSeries.candidate_id == candidate_id)
            .order_by(
                case((CandidateRelatedSeries.relation_type == "primary", 0), else_=1),
                CandidateRelatedSeries.id.asc(),
            )
            .limit(2)
        ).all()
    )
    primary_series = linked_series[0] if linked_series else None
    secondary_series = linked_series[1] if len(linked_series) > 1 else None
    primary_points = _series_points(db, primary_series.id, limit=60) if primary_series else []
    secondary_points = _series_points(db, secondary_series.id, limit=60) if secondary_series else []
    candidate_chart_data = _build_candidate_chart_data(
        primary_series=primary_series,
        primary_points=primary_points,
        secondary_series=secondary_series,
        secondary_points=secondary_points,
        include_comparison=bool(crosses),
    )
    publication_targets = list(
        db.scalars(
            select(PublicationTarget)
            .where(PublicationTarget.enabled.is_(True))
            .order_by(PublicationTarget.name.asc())
        ).all()
    )
    publication_count = db.scalar(
        select(func.count())
        .select_from(PublishedStory)
        .where(PublishedStory.candidate_id == candidate_id)
    )
    public_story = db.scalar(select(PublicStory).where(PublicStory.candidate_id == candidate_id))
    publish_defaults = _publish_form_defaults_from_state(candidate, draft, public_story)
    can_publish_web = ROLE_RANK.get(_auth.role, 0) >= ROLE_RANK["editor"]

    return templates.TemplateResponse(
        request=request,
        name="editorial/candidate_detail.html",
        context={
            "title": f"Candidate {candidate_id}",
            "candidate": candidate,
            "signals": signals,
            "score": score,
            "crosses": crosses,
            "draft": draft,
            "reviews": reviews,
            "sources": [f"{code} - {name}" for _, _, code, name in related_series_rows],
            "primary_series_id": related_series_rows[0][0] if related_series_rows else None,
            "candidate_chart_data": candidate_chart_data,
            "publication_targets": publication_targets,
            "publication_count": publication_count,
            "public_story": public_story,
            "publish_defaults": publish_defaults,
            "can_publish_web": can_publish_web,
            "message": message,
            "error": error,
        },
    )


@router.get("/signals")
def signals_view(
    request: Request,
    db: Session = DB_SESSION,
    _auth: AuthContext = VIEWER_AUTH,
    limit: int = 100,
    message: str | None = None,
    error: str | None = None,
):
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500

    signals = list(
        db.scalars(
            select(CandidateSignal).order_by(CandidateSignal.created_at.desc()).limit(limit)
        ).all()
    )
    candidates: dict[int, StoryCandidate] = {}
    if signals:
        candidates = {
            row.id: row
            for row in db.scalars(
                select(StoryCandidate).where(
                    StoryCandidate.id.in_([s.candidate_id for s in signals])
                )
            ).all()
        }

    return templates.TemplateResponse(
        request=request,
        name="editorial/signals.html",
        context={
            "title": "Signals",
            "signals": signals,
            "candidates": candidates,
            "limit": limit,
            "message": message,
            "error": error,
        },
    )


@router.get("/signals/{signal_id}/chart-data")
def signal_chart_data(
    signal_id: int,
    db: Session = DB_SESSION,
    _auth: AuthContext = VIEWER_AUTH,
) -> dict[str, object]:
    signal = db.get(CandidateSignal, signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    bundle = _signal_sparkline_bundle(db, signal)
    return {"signal_id": signal_id, **bundle}


@router.get("/signals/{signal_id}/sparkline", response_class=HTMLResponse)
def signal_sparkline_partial(
    request: Request,
    signal_id: int,
    db: Session = DB_SESSION,
    _auth: AuthContext = VIEWER_AUTH,
):
    signal = db.get(CandidateSignal, signal_id)
    if signal is None:
        return HTMLResponse('<span class="muted">Signal no encontrado</span>', status_code=404)
    bundle = _signal_sparkline_bundle(db, signal)
    return templates.TemplateResponse(
        request=request,
        name="editorial/partials/signal_sparkline.html",
        context={"signal": signal, **bundle},
    )


@router.get("/chart-audit")
def chart_audit_view(
    request: Request,
    db: Session = DB_SESSION,
    _auth: AuthContext = VIEWER_AUTH,
    days: int = 30,
    chart_type: str | None = None,
    chart_policy: str | None = None,
):
    if days not in {7, 30, 90}:
        days = 30
    chart_type = chart_type.strip() if chart_type else None
    chart_policy = chart_policy.strip() if chart_policy else None
    if chart_type == "":
        chart_type = None
    if chart_policy == "":
        chart_policy = None

    summary = _chart_audit_filtered(db, days=days, chart_type=chart_type, chart_policy=chart_policy)
    export_params: dict[str, str] = {"days": str(days)}
    if chart_type:
        export_params["chart_type"] = chart_type
    if chart_policy:
        export_params["chart_policy"] = chart_policy
    export_query = urlencode(export_params)

    return templates.TemplateResponse(
        request=request,
        name="editorial/chart_audit.html",
        context={
            "title": "Chart Audit",
            "days": days,
            "recent_candidates": summary["recent_candidates"],
            "type_chart": summary["type_chart"],
            "policy_chart": summary["policy_chart"],
            "chart_quality": summary["chart_quality"],
            "chart_type_options": summary["chart_type_options"],
            "chart_policy_options": summary["chart_policy_options"],
            "filter_chart_type": summary["filter_chart_type"],
            "filter_chart_policy": summary["filter_chart_policy"],
            "filtered_total": summary["filtered_total"],
            "table_row_cap": summary.get("table_row_cap", 500),
            "export_query": export_query,
        },
    )


@router.get("/chart-audit/export")
def chart_audit_export(
    db: Session = DB_SESSION,
    _auth: AuthContext = VIEWER_AUTH,
    days: int = 30,
    chart_type: str | None = None,
    chart_policy: str | None = None,
):
    if days not in {7, 30, 90}:
        days = 30
    chart_type = chart_type.strip() if chart_type else None
    chart_policy = chart_policy.strip() if chart_policy else None
    if chart_type == "":
        chart_type = None
    if chart_policy == "":
        chart_policy = None

    base = _audit_base_candidates(db, days, max_rows=2000)
    rows = _audit_apply_filters(base, chart_type=chart_type, chart_policy=chart_policy)

    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "title",
            "status",
            "chart_type_suggested",
            "chart_policy",
            "chart_rationale",
            "created_at",
        ]
    )
    for candidate in rows:
        spec = candidate.chart_spec_json or {}
        writer.writerow(
            [
                candidate.id,
                candidate.title,
                candidate.status,
                candidate.chart_type_suggested or "",
                spec.get("chart_policy") or "",
                (candidate.effective_chart_rationale or ""),
                candidate.created_at.isoformat() if candidate.created_at else "",
            ]
        )

    filename = f"chart-audit-{days}d.csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/signals/run")
def signals_run_action(
    limit_series: int = Form(default=200),
    db: Session = DB_SESSION,
    _auth: AuthContext = EDITOR_AUTH,
):
    if limit_series < 1:
        limit_series = 1
    try:
        payload = run_signal_pipeline(db, limit_series=limit_series)
        db.commit()
        return _redirect_to_signals(message=f"Pipeline ejecutado: {payload}")
    except ValueError as exc:
        db.rollback()
        return _redirect_to_signals(error=str(exc))


@router.post("/signals/simulate")
def signals_simulate_action(
    series_id: int = Form(...),
    db: Session = DB_SESSION,
    _auth: AuthContext = VIEWER_AUTH,
):
    try:
        signals = simulate_signals_for_series(db, series_id=series_id, overrides=None)
        return _redirect_to_signals(
            message=f"Simulacion para serie {series_id}: {len(signals)} senales"
        )
    except ValueError as exc:
        return _redirect_to_signals(error=str(exc))


@router.get("/published")
def published_view(
    request: Request,
    db: Session = DB_SESSION,
    _auth: AuthContext = VIEWER_AUTH,
    limit: int = 100,
    status: str | None = None,
):
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500

    public_story_stmt = select(PublicStory).order_by(
        PublicStory.updated_at.desc().nullslast(),
        PublicStory.id.desc(),
    ).limit(limit)
    if status:
        public_story_stmt = public_story_stmt.where(PublicStory.status == status)
    public_stories = list(db.scalars(public_story_stmt).all())

    public_story_status_options = [
        row[0]
        for row in db.execute(
            select(PublicStory.status).distinct().order_by(PublicStory.status.asc())
        ).all()
        if row[0]
    ]

    stmt = select(PublishedStory).order_by(PublishedStory.id.desc()).limit(limit)
    published_items = list(db.scalars(stmt).all())

    candidate_map: dict[int, StoryCandidate] = {}
    target_map: dict[int, PublicationTarget] = {}
    if published_items:
        candidate_map = {
            row.id: row
            for row in db.scalars(
                select(StoryCandidate).where(
                    StoryCandidate.id.in_([item.candidate_id for item in published_items])
                )
            ).all()
        }
        target_map = {
            row.id: row
            for row in db.scalars(
                select(PublicationTarget).where(
                    PublicationTarget.id.in_([item.target_id for item in published_items])
                )
            ).all()
        }
    return templates.TemplateResponse(
        request=request,
        name="editorial/published.html",
        context={
            "title": "Published",
            "public_stories": public_stories,
            "public_story_status_options": public_story_status_options,
            "selected_status": status or "",
            "limit": limit,
            "published_items": published_items,
            "candidate_map": candidate_map,
            "target_map": target_map,
        },
    )


def _redirect_with_notice(
    from_view: str,
    candidate_id: int,
    message: str | None = None,
    error: str | None = None,
):
    if from_view == "detail":
        base_path = f"/editorial/ui/candidates/{candidate_id}"
    else:
        base_path = "/editorial/ui/queue"
    query: dict[str, str] = {}
    if message:
        query["message"] = message
    if error:
        query["error"] = error
    suffix = f"?{urlencode(query)}" if query else ""
    return RedirectResponse(url=f"{base_path}{suffix}", status_code=303)


def _redirect_to_signals(message: str | None = None, error: str | None = None):
    query: dict[str, str] = {}
    if message:
        query["message"] = message
    if error:
        query["error"] = error
    suffix = f"?{urlencode(query)}" if query else ""
    return RedirectResponse(url=f"/editorial/ui/signals{suffix}", status_code=303)
