from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.editorial.models import CandidateSignal, SignalRule, StoryCandidate
from app.editorial.repositories.candidates import (
    add_signal,
    create_or_get_candidate,
    find_similar_candidate,
    get_candidate,
    get_candidate_by_hash,
    list_candidates,
    replace_crosses,
    set_related_company,
    set_related_series,
    upsert_draft,
    upsert_score,
)
from app.editorial.services.cross_suggester import suggest_crosses
from app.editorial.services.draft_generator import generate_draft_payload
from app.editorial.services.chart_recommender import suggest_chart_type
from app.editorial.services.score_engine import compute_candidate_score
from app.editorial.services.signal_detector import run_signal_detection
from app.models import Category, Series, Source


def _configured_rule_signal_types(db: Session) -> set[str]:
    aliases = {"historical_extreme": {"historical_max", "historical_min"}}
    types: set[str] = set()
    rows = db.scalars(select(SignalRule).where(SignalRule.enabled.is_(True))).all()
    for row in rows:
        types.update(aliases.get(row.signal_type, {row.signal_type}))
    return types


def run_signal_pipeline(db: Session, limit_series: int = 200) -> dict[str, int]:
    signals = run_signal_detection(db, limit_series=limit_series)
    configured_signal_types = _configured_rule_signal_types(db)
    series_meta_cache: dict[int, tuple[str | None, str | None, str | None]] = {}
    created = updated = signal_count = 0
    for s in signals:
        if s.signal_type in configured_signal_types and s.rule_id is None:
            raise ValueError(f"Missing rule_id for configured signal_type={s.signal_type}")
        existing = get_candidate_by_hash(db, s.dedupe_hash)
        if existing is None:
            existing = find_similar_candidate(
                db,
                title=s.title,
                insight=s.insight,
                geography=s.geography,
                period_label=s.period_label,
                threshold=0.92,
            )
        candidate = create_or_get_candidate(
            db,
            dedupe_hash=existing.dedupe_hash if existing else s.dedupe_hash,
            title=s.title,
            insight=s.insight,
            executive_summary=s.executive_summary,
            why_it_matters=s.why_it_matters,
            geography=s.geography,
            period_label=s.period_label,
        )
        if existing is None:
            created += 1
        else:
            updated += 1
        if s.series_id is not None:
            set_related_series(db, candidate.id, s.series_id)
            if s.series_id not in series_meta_cache:
                row = db.execute(
                    select(Source.slug, Category.name, Series.name)
                    .select_from(Series)
                    .join(Source, Source.id == Series.source_id)
                    .outerjoin(Category, Category.id == Series.category_id)
                    .where(Series.id == s.series_id)
                ).first()
                series_meta_cache[s.series_id] = (row[0], row[1], row[2]) if row else (None, None, None)
        if s.company_id is not None:
            set_related_company(db, candidate.id, s.company_id)
        add_signal(
            db,
            candidate_id=candidate.id,
            signal_type=s.signal_type,
            signal_key=s.signal_key,
            explanation=s.explanation,
            strength=s.strength,
            rule_id=s.rule_id,
            payload_json={"series_id": s.series_id, "company_id": s.company_id},
        )
        source_slug = None
        category_name = None
        series_name = None
        if s.series_id is not None:
            source_slug, category_name, series_name = series_meta_cache.get(
                s.series_id, (None, None, None)
            )
        suggested_chart_type, chart_rationale = suggest_chart_type(
            candidate,
            source_slugs=[source_slug] if source_slug else [],
            category_names=[category_name] if category_name else [],
            signal_types=[s.signal_type],
            series_names=[series_name] if series_name else [],
            series_count=2 if s.signal_type == "series_divergence" else 1,
            has_spatial_data=bool(s.geography),
        )
        candidate.chart_type_suggested = suggested_chart_type
        candidate.chart_rationale = chart_rationale
        spec = dict(candidate.chart_spec_json or {})
        spec["chart_rationale"] = chart_rationale
        spec["chart_policy"] = "topic_default_v2"
        candidate.chart_spec_json = spec
        signal_count += 1
    return {"signals_detected": len(signals), "signals_written": signal_count, "created": created, "updated": updated}


def score_candidate(db: Session, candidate_id: int) -> dict[str, object]:
    values, rationale = compute_candidate_score(db, candidate_id)
    row = upsert_score(db, candidate_id, values, rationale)
    return {
        "candidate_id": row.candidate_id,
        "total_score": row.total_score,
        "rationale": row.rationale,
    }


def draft_candidate(db: Session, candidate_id: int) -> dict[str, object]:
    candidate = get_candidate(db, candidate_id)
    if not candidate:
        raise ValueError("Candidate not found")
    payload = generate_draft_payload(candidate)
    row = upsert_draft(db, candidate_id, payload)
    return {"candidate_id": row.candidate_id}


def suggest_candidate_crosses(db: Session, candidate_id: int) -> list[dict[str, str]]:
    candidate = get_candidate(db, candidate_id)
    if not candidate:
        raise ValueError("Candidate not found")
    crosses = suggest_crosses(candidate)
    replace_crosses(db, candidate_id, crosses)
    return crosses


def dashboard_stats(db: Session) -> dict[str, int]:
    total = db.scalar(select(func.count()).select_from(StoryCandidate)) or 0
    reviewing = db.scalar(
        select(func.count()).select_from(StoryCandidate).where(StoryCandidate.status == "reviewing")
    ) or 0
    new = db.scalar(select(func.count()).select_from(StoryCandidate).where(StoryCandidate.status == "new")) or 0
    shortlisted = db.scalar(
        select(func.count()).select_from(StoryCandidate).where(StoryCandidate.status == "shortlisted")
    ) or 0
    published = db.scalar(
        select(func.count()).select_from(StoryCandidate).where(StoryCandidate.status == "published")
    ) or 0
    signals = db.scalar(select(func.count()).select_from(CandidateSignal)) or 0
    return {
        "candidates_total": int(total),
        "candidates_new": int(new),
        "candidates_reviewing": int(reviewing),
        "candidates_shortlisted": int(shortlisted),
        "candidates_published": int(published),
        "signals_total": int(signals),
    }


def list_queue(db: Session, limit: int = 100) -> list[StoryCandidate]:
    return list_candidates(db, status="new", limit=limit)


def editorial_full_dashboard(db: Session, recent_limit: int = 10) -> dict[str, object]:
    from app.editorial.services.rule_service import (
        detect_rule_accuracy_alerts,
        impact_accuracy_leaderboard,
    )

    base = dashboard_stats(db)
    recent_candidates = list(
        db.scalars(select(StoryCandidate).order_by(StoryCandidate.created_at.desc()).limit(recent_limit)).all()
    )
    leaderboard = impact_accuracy_leaderboard(db, limit=10)
    alerts = detect_rule_accuracy_alerts(db, min_evaluations=2, error_threshold=2.0, limit=25)
    return {
        "overview": base,
        "accuracy_leaderboard": leaderboard,
        "rule_alerts": alerts,
        "recent_candidates": [
            {
                "id": c.id,
                "title": c.title,
                "status": c.status,
                "score_total": float(c.score_total) if c.score_total is not None else None,
                "created_at": c.created_at,
            }
            for c in recent_candidates
        ],
    }
