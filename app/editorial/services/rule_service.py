from __future__ import annotations

from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.editorial.models import (
    CandidateSignal,
    SignalRuleImpactEvaluation,
    SignalRule,
    SignalRuleImpactPreview,
    SignalRuleRevision,
)
from app.editorial.schemas.common import SignalRuleUpsert
from app.editorial.services.candidate_service import run_signal_pipeline
from app.editorial.services.signal_detector import (
    build_rule_map_with_overrides,
    run_signal_detection,
    run_signal_detection_with_rule_map,
)


def list_rules(db: Session) -> list[SignalRule]:
    return list(db.scalars(select(SignalRule).order_by(SignalRule.signal_type, SignalRule.slug)).all())


def get_rule(db: Session, rule_id: int) -> SignalRule | None:
    return db.get(SignalRule, rule_id)


def list_rule_revisions(db: Session, rule_id: int, limit: int = 100) -> list[SignalRuleRevision]:
    return list(
        db.scalars(
            select(SignalRuleRevision)
            .where(SignalRuleRevision.rule_id == rule_id)
            .order_by(SignalRuleRevision.id.desc())
            .limit(limit)
        ).all()
    )


def get_rule_revision(db: Session, revision_id: int) -> SignalRuleRevision | None:
    return db.get(SignalRuleRevision, revision_id)


def list_impact_previews(db: Session, rule_id: int, limit: int = 50) -> list[SignalRuleImpactPreview]:
    return list(
        db.scalars(
            select(SignalRuleImpactPreview)
            .where(SignalRuleImpactPreview.rule_id == rule_id)
            .order_by(SignalRuleImpactPreview.id.desc())
            .limit(limit)
        ).all()
    )


def get_impact_preview(db: Session, preview_id: int) -> SignalRuleImpactPreview | None:
    return db.get(SignalRuleImpactPreview, preview_id)


def list_impact_evaluations(
    db: Session,
    preview_id: int,
    limit: int = 50,
) -> list[SignalRuleImpactEvaluation]:
    return list(
        db.scalars(
            select(SignalRuleImpactEvaluation)
            .where(SignalRuleImpactEvaluation.preview_id == preview_id)
            .order_by(SignalRuleImpactEvaluation.id.desc())
            .limit(limit)
        ).all()
    )


def get_impact_evaluation(db: Session, evaluation_id: int) -> SignalRuleImpactEvaluation | None:
    return db.get(SignalRuleImpactEvaluation, evaluation_id)


def impact_accuracy_leaderboard(db: Session, limit: int = 20) -> list[dict[str, object]]:
    evaluations = list(
        db.scalars(select(SignalRuleImpactEvaluation).order_by(SignalRuleImpactEvaluation.id.desc()).limit(2000)).all()
    )
    grouped: dict[int, list[SignalRuleImpactEvaluation]] = {}
    for row in evaluations:
        grouped.setdefault(row.rule_id, []).append(row)

    output: list[dict[str, object]] = []
    for rule_id, rows in grouped.items():
        rule = db.get(SignalRule, rule_id)
        if not rule:
            continue
        signal_abs_errors: list[float] = []
        candidate_abs_errors: list[float] = []
        signal_pct_errors: list[float] = []
        candidate_pct_errors: list[float] = []
        for row in rows:
            metrics = row.metrics_json if isinstance(row.metrics_json, dict) else {}
            sa = metrics.get("signal_abs_error")
            ca = metrics.get("candidate_abs_error")
            sp = metrics.get("signal_pct_error")
            cp = metrics.get("candidate_pct_error")
            if isinstance(sa, (int, float)):
                signal_abs_errors.append(float(sa))
            if isinstance(ca, (int, float)):
                candidate_abs_errors.append(float(ca))
            if isinstance(sp, (int, float)):
                signal_pct_errors.append(float(sp))
            if isinstance(cp, (int, float)):
                candidate_pct_errors.append(float(cp))

        n = len(rows)
        mae_signal = (sum(signal_abs_errors) / len(signal_abs_errors)) if signal_abs_errors else None
        mae_candidate = (sum(candidate_abs_errors) / len(candidate_abs_errors)) if candidate_abs_errors else None
        mape_signal = (sum(signal_pct_errors) / len(signal_pct_errors)) if signal_pct_errors else None
        mape_candidate = (sum(candidate_pct_errors) / len(candidate_pct_errors)) if candidate_pct_errors else None
        combined_error = (
            (mae_signal or 0.0) + (mae_candidate or 0.0) + ((mape_signal or 0.0) / 100) + ((mape_candidate or 0.0) / 100)
        )
        output.append(
            {
                "rule_id": rule.id,
                "rule_slug": rule.slug,
                "signal_type": rule.signal_type,
                "evaluations_count": n,
                "mae_signal": mae_signal,
                "mae_candidate": mae_candidate,
                "mape_signal": mape_signal,
                "mape_candidate": mape_candidate,
                "combined_error_score": round(combined_error, 6),
                "stability_label": "stable" if combined_error < 2 else "watch",
            }
        )

    output.sort(key=lambda x: (x["combined_error_score"], -x["evaluations_count"]))
    return output[:limit]


def impact_accuracy_trend_for_rule(
    db: Session,
    rule_id: int,
    window_size: int = 5,
    limit: int = 100,
) -> dict[str, object]:
    rule = db.get(SignalRule, rule_id)
    if not rule:
        raise ValueError("Rule not found")
    rows = list(
        db.scalars(
            select(SignalRuleImpactEvaluation)
            .where(SignalRuleImpactEvaluation.rule_id == rule_id)
            .order_by(SignalRuleImpactEvaluation.created_at.asc())
            .limit(limit)
        ).all()
    )
    points: list[dict[str, object]] = []
    running_signal_abs: list[float] = []
    running_candidate_abs: list[float] = []
    running_signal_pct: list[float] = []
    running_candidate_pct: list[float] = []
    for row in rows:
        metrics = row.metrics_json if isinstance(row.metrics_json, dict) else {}
        sa = metrics.get("signal_abs_error")
        ca = metrics.get("candidate_abs_error")
        sp = metrics.get("signal_pct_error")
        cp = metrics.get("candidate_pct_error")
        running_signal_abs.append(float(sa) if isinstance(sa, (int, float)) else 0.0)
        running_candidate_abs.append(float(ca) if isinstance(ca, (int, float)) else 0.0)
        running_signal_pct.append(float(sp) if isinstance(sp, (int, float)) else 0.0)
        running_candidate_pct.append(float(cp) if isinstance(cp, (int, float)) else 0.0)
        window_sa = running_signal_abs[-window_size:]
        window_ca = running_candidate_abs[-window_size:]
        window_sp = running_signal_pct[-window_size:]
        window_cp = running_candidate_pct[-window_size:]
        rolling = {
            "mae_signal": round(sum(window_sa) / len(window_sa), 6),
            "mae_candidate": round(sum(window_ca) / len(window_ca), 6),
            "mape_signal": round(sum(window_sp) / len(window_sp), 6),
            "mape_candidate": round(sum(window_cp) / len(window_cp), 6),
        }
        points.append(
            {
                "evaluation_id": row.id,
                "created_at": row.created_at,
                "rolling_metrics": rolling,
            }
        )
    latest = points[-1]["rolling_metrics"] if points else None
    return {
        "rule_id": rule.id,
        "rule_slug": rule.slug,
        "signal_type": rule.signal_type,
        "window_size": window_size,
        "points": points,
        "latest_rolling_metrics": latest,
    }


def detect_rule_accuracy_alerts(
    db: Session,
    min_evaluations: int = 3,
    error_threshold: float = 2.0,
    limit: int = 50,
) -> list[dict[str, object]]:
    leaderboard = impact_accuracy_leaderboard(db, limit=limit)
    alerts: list[dict[str, object]] = []
    for row in leaderboard:
        if row["evaluations_count"] < min_evaluations:
            continue
        if row["combined_error_score"] >= error_threshold or row["stability_label"] == "watch":
            alerts.append(
                {
                    "rule_id": row["rule_id"],
                    "rule_slug": row["rule_slug"],
                    "signal_type": row["signal_type"],
                    "evaluations_count": row["evaluations_count"],
                    "combined_error_score": row["combined_error_score"],
                    "severity": "high" if row["combined_error_score"] >= error_threshold * 1.5 else "medium",
                }
            )
    return alerts


def _snapshot_rule(row: SignalRule) -> dict[str, object]:
    return {
        "slug": row.slug,
        "name": row.name,
        "signal_type": row.signal_type,
        "params_json": row.params_json,
        "weight": str(row.weight),
        "enabled": row.enabled,
        "description": row.description,
    }


def _write_revision(db: Session, row: SignalRule, action: str, actor: str | None) -> SignalRuleRevision:
    rev = SignalRuleRevision(rule_id=row.id, action=action, actor=actor, snapshot_json=_snapshot_rule(row))
    db.add(rev)
    db.flush()
    return rev


def create_rule(db: Session, payload: SignalRuleUpsert, actor: str | None = None) -> SignalRule:
    exists = db.scalar(select(SignalRule).where(SignalRule.slug == payload.slug))
    if exists:
        raise ValueError("Rule slug already exists")
    row = SignalRule(**payload.model_dump())
    db.add(row)
    db.flush()
    _write_revision(db, row, action="create", actor=actor)
    return row


def update_rule(db: Session, rule_id: int, payload: SignalRuleUpsert, actor: str | None = None) -> SignalRule:
    row = db.get(SignalRule, rule_id)
    if not row:
        raise ValueError("Rule not found")
    duplicate = db.scalar(select(SignalRule).where(SignalRule.slug == payload.slug, SignalRule.id != rule_id))
    if duplicate:
        raise ValueError("Rule slug already exists")
    _write_revision(db, row, action="before_update", actor=actor)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.flush()
    _write_revision(db, row, action="after_update", actor=actor)
    return row


def delete_rule(db: Session, rule_id: int, actor: str | None = None) -> None:
    row = db.get(SignalRule, rule_id)
    if not row:
        raise ValueError("Rule not found")
    _write_revision(db, row, action="delete", actor=actor)
    db.delete(row)


def recompute_for_rule(db: Session, rule_id: int, limit_series: int = 200) -> dict[str, int]:
    rule = db.get(SignalRule, rule_id)
    if not rule:
        raise ValueError("Rule not found")
    pipeline_result = run_signal_pipeline(db, limit_series=limit_series)
    matched_count = db.scalar(
        select(func.count())
        .select_from(CandidateSignal)
        .where(CandidateSignal.signal_type == rule.signal_type)
    )
    return {
        "rule_id": rule.id,
        "signal_type": rule.signal_type,
        "matched_signals": int(matched_count or 0),
        **pipeline_result,
    }


def rollback_rule_to_revision(
    db: Session, rule_id: int, revision_id: int, actor: str | None = None
) -> SignalRule:
    rule = db.get(SignalRule, rule_id)
    if not rule:
        raise ValueError("Rule not found")
    revision = db.get(SignalRuleRevision, revision_id)
    if not revision or revision.rule_id != rule_id:
        raise ValueError("Revision not found for rule")
    snapshot = revision.snapshot_json
    payload = SignalRuleUpsert(
        slug=str(snapshot["slug"]),
        name=str(snapshot["name"]),
        signal_type=str(snapshot["signal_type"]),
        params_json=snapshot.get("params_json") if isinstance(snapshot.get("params_json"), dict) else None,
        weight=snapshot.get("weight", "1"),
        enabled=bool(snapshot.get("enabled", True)),
        description=str(snapshot["description"]) if snapshot.get("description") is not None else None,
    )
    _write_revision(db, rule, action="before_rollback", actor=actor)
    for key, value in payload.model_dump().items():
        setattr(rule, key, value)
    db.flush()
    _write_revision(db, rule, action="after_rollback", actor=actor)
    return rule


def _normalize_snapshot(snapshot: dict[str, object]) -> dict[str, object]:
    normalized = dict(snapshot)
    params = normalized.get("params_json")
    normalized["params_json"] = params if isinstance(params, dict) else {}
    weight = normalized.get("weight")
    if weight is not None:
        normalized["weight"] = str(weight)
    return normalized


def diff_rule_revisions(
    db: Session,
    rule_id: int,
    revision_a_id: int,
    revision_b_id: int,
) -> dict[str, object]:
    rule = db.get(SignalRule, rule_id)
    if not rule:
        raise ValueError("Rule not found")
    rev_a = db.get(SignalRuleRevision, revision_a_id)
    rev_b = db.get(SignalRuleRevision, revision_b_id)
    if not rev_a or rev_a.rule_id != rule_id:
        raise ValueError("Revision A not found for rule")
    if not rev_b or rev_b.rule_id != rule_id:
        raise ValueError("Revision B not found for rule")

    snap_a = _normalize_snapshot(rev_a.snapshot_json)
    snap_b = _normalize_snapshot(rev_b.snapshot_json)

    changed_fields: dict[str, dict[str, object]] = {}
    for key in ["slug", "name", "signal_type", "weight", "enabled", "description"]:
        if snap_a.get(key) != snap_b.get(key):
            changed_fields[key] = {"from": snap_a.get(key), "to": snap_b.get(key)}

    params_a = snap_a["params_json"] if isinstance(snap_a.get("params_json"), dict) else {}
    params_b = snap_b["params_json"] if isinstance(snap_b.get("params_json"), dict) else {}
    all_param_keys = sorted(set(params_a.keys()) | set(params_b.keys()))
    params_diff: dict[str, dict[str, object]] = {}
    for key in all_param_keys:
        if params_a.get(key) != params_b.get(key):
            params_diff[key] = {"from": params_a.get(key), "to": params_b.get(key)}

    magnitude = Decimal("0")
    magnitude += Decimal(len(changed_fields))
    magnitude += Decimal(len(params_diff)) * Decimal("0.5")

    return {
        "rule_id": rule_id,
        "revision_a_id": revision_a_id,
        "revision_b_id": revision_b_id,
        "revision_a_action": rev_a.action,
        "revision_b_action": rev_b.action,
        "changed_fields": changed_fields,
        "params_diff": params_diff,
        "total_changes": len(changed_fields) + len(params_diff),
        "change_magnitude_score": str(magnitude),
    }


CRITICAL_THRESHOLD_KEYS = {
    "mom_threshold_pct",
    "yoy_threshold_pct",
    "trend_threshold_pct",
    "zscore_threshold",
    "divergence_threshold_pct",
}


def build_rule_timeline(db: Session, rule_id: int, limit: int = 100) -> dict[str, object]:
    rule = db.get(SignalRule, rule_id)
    if not rule:
        raise ValueError("Rule not found")
    revisions = list(
        db.scalars(
            select(SignalRuleRevision)
            .where(SignalRuleRevision.rule_id == rule_id)
            .order_by(SignalRuleRevision.id.asc())
            .limit(limit)
        ).all()
    )
    items: list[dict[str, object]] = []
    critical_events = 0
    for idx, rev in enumerate(revisions):
        current = _normalize_snapshot(rev.snapshot_json)
        if idx == 0:
            change_summary = {"changed_fields": {}, "params_diff": {}, "is_critical": False}
            items.append(
                {
                    "revision_id": rev.id,
                    "action": rev.action,
                    "actor": rev.actor,
                    "created_at": rev.created_at,
                    "change_summary": change_summary,
                    "snapshot": current,
                }
            )
            continue
        prev = _normalize_snapshot(revisions[idx - 1].snapshot_json)
        changed_fields: dict[str, dict[str, object]] = {}
        for key in ["slug", "name", "signal_type", "weight", "enabled", "description"]:
            if prev.get(key) != current.get(key):
                changed_fields[key] = {"from": prev.get(key), "to": current.get(key)}
        params_prev = prev.get("params_json") if isinstance(prev.get("params_json"), dict) else {}
        params_cur = current.get("params_json") if isinstance(current.get("params_json"), dict) else {}
        params_diff: dict[str, dict[str, object]] = {}
        for key in sorted(set(params_prev.keys()) | set(params_cur.keys())):
            if params_prev.get(key) != params_cur.get(key):
                params_diff[key] = {"from": params_prev.get(key), "to": params_cur.get(key)}
        critical_keys = [k for k in params_diff.keys() if k in CRITICAL_THRESHOLD_KEYS]
        is_critical = len(critical_keys) > 0
        if is_critical:
            critical_events += 1
        items.append(
            {
                "revision_id": rev.id,
                "action": rev.action,
                "actor": rev.actor,
                "created_at": rev.created_at,
                "change_summary": {
                    "changed_fields": changed_fields,
                    "params_diff": params_diff,
                    "critical_keys": critical_keys,
                    "is_critical": is_critical,
                },
                "snapshot": current,
            }
        )
    return {
        "rule_id": rule_id,
        "rule_slug": rule.slug,
        "total_revisions": len(revisions),
        "critical_events": critical_events,
        "timeline": items,
    }


def impact_preview_for_rule(
    db: Session,
    rule_id: int,
    override_params: dict[str, object] | None = None,
    limit_series: int = 200,
) -> dict[str, object]:
    rule = db.get(SignalRule, rule_id)
    if not rule:
        raise ValueError("Rule not found")

    baseline = run_signal_detection(db, limit_series=limit_series)
    baseline_for_rule = [s for s in baseline if s.signal_type == rule.signal_type]
    baseline_keys = {s.signal_key for s in baseline_for_rule}
    baseline_candidates = {s.dedupe_hash for s in baseline_for_rule}

    overridden_rule_map = build_rule_map_with_overrides(
        db, signal_type=rule.signal_type, override_params=override_params
    )
    simulated = run_signal_detection_with_rule_map(
        db, rule_map=overridden_rule_map, limit_series=limit_series
    )
    simulated_for_rule = [s for s in simulated if s.signal_type == rule.signal_type]
    simulated_keys = {s.signal_key for s in simulated_for_rule}
    simulated_candidates = {s.dedupe_hash for s in simulated_for_rule}

    added_keys = sorted(simulated_keys - baseline_keys)
    removed_keys = sorted(baseline_keys - simulated_keys)
    kept_keys = sorted(simulated_keys & baseline_keys)

    impact_score = Decimal("0")
    impact_score += Decimal(len(added_keys))
    impact_score += Decimal(len(removed_keys))
    impact_score += Decimal(abs(len(simulated_candidates) - len(baseline_candidates))) * Decimal("0.5")

    return {
        "rule_id": rule.id,
        "signal_type": rule.signal_type,
        "limit_series": limit_series,
        "baseline": {
            "signals_count": len(baseline_for_rule),
            "candidate_count": len(baseline_candidates),
        },
        "simulated": {
            "signals_count": len(simulated_for_rule),
            "candidate_count": len(simulated_candidates),
        },
        "delta": {
            "signals_added": len(added_keys),
            "signals_removed": len(removed_keys),
            "candidates_delta": len(simulated_candidates) - len(baseline_candidates),
        },
        "examples": {
            "added_signal_keys": added_keys[:10],
            "removed_signal_keys": removed_keys[:10],
            "kept_signal_keys": kept_keys[:10],
        },
        "impact_score": str(impact_score),
        "override_params": override_params or {},
    }


def create_impact_preview_record(
    db: Session,
    *,
    rule_id: int,
    actor: str | None,
    limit_series: int,
    override_params: dict[str, object] | None,
    result: dict[str, object],
) -> SignalRuleImpactPreview:
    row = SignalRuleImpactPreview(
        rule_id=rule_id,
        actor=actor,
        limit_series=limit_series,
        override_params_json=override_params or {},
        result_json=result,
    )
    db.add(row)
    db.flush()
    return row


def evaluate_impact_preview(
    db: Session,
    preview_id: int,
    actor: str | None = None,
) -> SignalRuleImpactEvaluation:
    preview = db.get(SignalRuleImpactPreview, preview_id)
    if not preview:
        raise ValueError("Impact preview not found")
    rule = db.get(SignalRule, preview.rule_id)
    if not rule:
        raise ValueError("Rule not found")

    predicted = dict(preview.result_json or {})
    predicted_baseline = predicted.get("baseline", {}) if isinstance(predicted.get("baseline"), dict) else {}
    predicted_simulated = predicted.get("simulated", {}) if isinstance(predicted.get("simulated"), dict) else {}
    override_params = (
        preview.override_params_json if isinstance(preview.override_params_json, dict) else None
    )

    actual = impact_preview_for_rule(
        db,
        rule_id=rule.id,
        override_params=override_params,
        limit_series=preview.limit_series,
    )

    predicted_signal_count = int(predicted_simulated.get("signals_count", 0))
    predicted_candidate_count = int(predicted_simulated.get("candidate_count", 0))
    actual_signal_count = int(actual.get("simulated", {}).get("signals_count", 0))
    actual_candidate_count = int(actual.get("simulated", {}).get("candidate_count", 0))

    signal_abs_error = abs(predicted_signal_count - actual_signal_count)
    candidate_abs_error = abs(predicted_candidate_count - actual_candidate_count)
    signal_pct_error = (
        round((signal_abs_error / actual_signal_count) * 100, 2) if actual_signal_count > 0 else None
    )
    candidate_pct_error = (
        round((candidate_abs_error / actual_candidate_count) * 100, 2) if actual_candidate_count > 0 else None
    )

    metrics = {
        "evaluation_mode": "simulated_vs_simulated_with_same_overrides",
        "signal_abs_error": signal_abs_error,
        "candidate_abs_error": candidate_abs_error,
        "signal_pct_error": signal_pct_error,
        "candidate_pct_error": candidate_pct_error,
        "predicted_baseline": predicted_baseline,
        "override_params": override_params or {},
    }
    row = SignalRuleImpactEvaluation(
        preview_id=preview.id,
        rule_id=rule.id,
        actor=actor,
        predicted_json=predicted,
        actual_json={"current": actual},
        metrics_json=metrics,
    )
    db.add(row)
    db.flush()
    return row
