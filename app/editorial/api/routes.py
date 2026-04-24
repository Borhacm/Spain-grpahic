from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import require_role
from app.editorial.models import (
    CandidateDraft,
    CandidateScore,
    CandidateSignal,
    PublishedStory,
    SignalRuleImpactEvaluation,
    SignalRuleImpactPreview,
    SignalRuleRevision,
)
from app.editorial.repositories.candidates import get_candidate, list_candidates
from app.editorial.schemas.common import CandidateOut, DraftOut, ScoreOut, SignalOut
from app.editorial.services.candidate_service import (
    dashboard_stats,
    draft_candidate,
    editorial_full_dashboard,
    list_queue,
    run_signal_pipeline,
    score_candidate,
    suggest_candidate_crosses,
)
from app.editorial.schemas.public_api import PublishCandidatePayload, PublishPublicStoryResponse
from app.editorial.services.public_story_service import publish_candidate
from app.editorial.services.publication_service import send_to_publication_target
from app.editorial.services.review_service import set_candidate_state
from app.editorial.services.signal_detector import simulate_signals_for_series
from app.editorial.services.rule_service import (
    build_rule_timeline,
    create_rule,
    create_impact_preview_record,
    delete_rule,
    diff_rule_revisions,
    evaluate_impact_preview,
    get_rule,
    get_impact_evaluation,
    get_impact_preview,
    get_rule_revision,
    impact_preview_for_rule,
    list_impact_evaluations,
    impact_accuracy_leaderboard,
    impact_accuracy_trend_for_rule,
    list_impact_previews,
    list_rules,
    list_rule_revisions,
    recompute_for_rule,
    rollback_rule_to_revision,
    detect_rule_accuracy_alerts,
    update_rule,
)
from app.editorial.schemas.common import (
    CandidateCrossesResponse,
    PublishedStoryOut,
    DashboardFullResponse,
    DashboardOverviewResponse,
    ImpactPreviewRequest,
    ImpactPreviewResponse,
    RuleAccuracyAlertsResponse,
    RuleAccuracyLeaderboardResponse,
    RuleAccuracyTrendResponse,
    RuleDeleteResponse,
    RuleRecomputeResponse,
    RuleRevisionDiffResponse,
    RuleTimelineResponse,
    SendToCmsResponse,
    SimulateSignalsRequest,
    SimulateSignalsResponse,
    SignalRuleImpactEvaluationOut,
    SignalRuleImpactPreviewOut,
    SignalRuleOut,
    SignalRuleRevisionOut,
    SignalRuleUpsert,
)

router = APIRouter(tags=["editorial"], dependencies=[require_role("viewer")])


@router.get("/signals", response_model=list[SignalOut])
def get_signals(db: Session = Depends(get_db), limit: int = 100) -> list[CandidateSignal]:
    return list(db.scalars(select(CandidateSignal).order_by(CandidateSignal.created_at.desc()).limit(limit)).all())


@router.post("/signals/run")
def post_run_signals(
    db: Session = Depends(get_db), limit_series: int = 200, _auth=require_role("editor")
) -> dict[str, int]:
    payload = run_signal_pipeline(db, limit_series=limit_series)
    db.commit()
    return payload


@router.post("/signals/simulate", response_model=SimulateSignalsResponse)
def simulate_signals(
    series_id: int,
    db: Session = Depends(get_db),
    payload: SimulateSignalsRequest | None = None,
) -> SimulateSignalsResponse:
    try:
        overrides = payload.overrides if payload else None
        signals = simulate_signals_for_series(db, series_id=series_id, overrides=overrides)
        return SimulateSignalsResponse(
            series_id=series_id,
            signals_count=len(signals),
            signals=[
                {
                    "signal_type": s.signal_type,
                    "signal_key": s.signal_key,
                    "explanation": s.explanation,
                    "strength": str(s.strength),
                    "period_label": s.period_label,
                }
                for s in signals
            ],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/signals/{signal_id}", response_model=SignalOut)
def get_signal(signal_id: int, db: Session = Depends(get_db)) -> CandidateSignal:
    row = db.get(CandidateSignal, signal_id)
    if not row:
        raise HTTPException(status_code=404, detail="Signal not found")
    return row


@router.get("/signal-rules", response_model=list[SignalRuleOut])
def get_signal_rules(db: Session = Depends(get_db)):
    return list_rules(db)


@router.get("/signal-rules/{rule_id:int}", response_model=SignalRuleOut)
def get_signal_rule(rule_id: int, db: Session = Depends(get_db)):
    row = get_rule(db, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    return row


@router.post("/signal-rules", response_model=SignalRuleOut)
def post_signal_rule(
    payload: SignalRuleUpsert, db: Session = Depends(get_db), actor: str | None = None, _auth=require_role("editor")
):
    try:
        row = create_rule(db, payload, actor=actor)
        db.commit()
        return row
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/signal-rules/{rule_id:int}", response_model=SignalRuleOut)
def put_signal_rule(
    rule_id: int,
    payload: SignalRuleUpsert,
    db: Session = Depends(get_db),
    actor: str | None = None,
    _auth=require_role("editor"),
):
    try:
        row = update_rule(db, rule_id, payload, actor=actor)
        db.commit()
        return row
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/signal-rules/{rule_id:int}", response_model=RuleDeleteResponse)
def remove_signal_rule(
    rule_id: int, db: Session = Depends(get_db), actor: str | None = None, _auth=require_role("admin")
) -> RuleDeleteResponse:
    try:
        delete_rule(db, rule_id, actor=actor)
        db.commit()
        return {"deleted": True, "rule_id": rule_id}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/signal-rules/{rule_id:int}/recompute", response_model=RuleRecomputeResponse)
def post_recompute_rule(
    rule_id: int, db: Session = Depends(get_db), limit_series: int = 200, _auth=require_role("editor")
) -> RuleRecomputeResponse:
    try:
        payload = recompute_for_rule(db, rule_id=rule_id, limit_series=limit_series)
        db.commit()
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/signal-rules/{rule_id:int}/revisions", response_model=list[SignalRuleRevisionOut])
def get_rule_revisions(rule_id: int, db: Session = Depends(get_db), limit: int = 100):
    return list_rule_revisions(db, rule_id=rule_id, limit=limit)


@router.get("/signal-rule-revisions/{revision_id}", response_model=SignalRuleRevisionOut)
def get_revision(revision_id: int, db: Session = Depends(get_db)) -> SignalRuleRevision:
    row = get_rule_revision(db, revision_id)
    if not row:
        raise HTTPException(status_code=404, detail="Revision not found")
    return row


@router.post("/signal-rules/{rule_id:int}/rollback/{revision_id:int}", response_model=SignalRuleOut)
def rollback_rule(
    rule_id: int,
    revision_id: int,
    db: Session = Depends(get_db),
    actor: str | None = None,
    _auth=require_role("admin"),
):
    try:
        row = rollback_rule_to_revision(db, rule_id=rule_id, revision_id=revision_id, actor=actor)
        db.commit()
        return row
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/signal-rules/{rule_id:int}/revisions/{revision_a_id:int}/diff/{revision_b_id:int}",
    response_model=RuleRevisionDiffResponse,
)
def get_rule_revision_diff(
    rule_id: int,
    revision_a_id: int,
    revision_b_id: int,
    db: Session = Depends(get_db),
) -> RuleRevisionDiffResponse:
    try:
        return diff_rule_revisions(
            db,
            rule_id=rule_id,
            revision_a_id=revision_a_id,
            revision_b_id=revision_b_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/signal-rules/{rule_id:int}/timeline", response_model=RuleTimelineResponse)
def get_rule_timeline(
    rule_id: int,
    db: Session = Depends(get_db),
    limit: int = 100,
    critical_only: bool = False,
) -> RuleTimelineResponse:
    try:
        payload = build_rule_timeline(db, rule_id=rule_id, limit=limit)
        if critical_only:
            payload["timeline"] = [
                item
                for item in payload["timeline"]
                if item["change_summary"].get("is_critical") is True
            ]
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/signal-rules/{rule_id:int}/impact-preview", response_model=ImpactPreviewResponse)
def post_rule_impact_preview(
    rule_id: int,
    db: Session = Depends(get_db),
    limit_series: int = 200,
    payload: ImpactPreviewRequest | None = None,
    persist: bool = True,
    actor: str | None = None,
    _auth=require_role("editor"),
) -> ImpactPreviewResponse:
    try:
        override_params = payload.override_params if payload else None
        result = impact_preview_for_rule(
            db,
            rule_id=rule_id,
            override_params=override_params,
            limit_series=limit_series,
        )
        preview_id = None
        if persist:
            row = create_impact_preview_record(
                db,
                rule_id=rule_id,
                actor=actor,
                limit_series=limit_series,
                override_params=override_params if isinstance(override_params, dict) else None,
                result=result,
            )
            db.commit()
            preview_id = row.id
        result["preview_id"] = preview_id
        return ImpactPreviewResponse.model_validate(result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/signal-rules/{rule_id:int}/impact-previews", response_model=list[SignalRuleImpactPreviewOut])
def get_rule_impact_previews(
    rule_id: int,
    db: Session = Depends(get_db),
    limit: int = 50,
):
    return list_impact_previews(db, rule_id=rule_id, limit=limit)


@router.get("/signal-rule-impact-previews/{preview_id}", response_model=SignalRuleImpactPreviewOut)
def get_rule_impact_preview(preview_id: int, db: Session = Depends(get_db)) -> SignalRuleImpactPreview:
    row = get_impact_preview(db, preview_id)
    if not row:
        raise HTTPException(status_code=404, detail="Impact preview not found")
    return row


@router.post(
    "/signal-rule-impact-previews/{preview_id}/evaluate",
    response_model=SignalRuleImpactEvaluationOut,
)
def post_impact_preview_evaluate(
    preview_id: int,
    db: Session = Depends(get_db),
    actor: str | None = None,
    _auth=require_role("editor"),
) -> SignalRuleImpactEvaluation:
    try:
        row = evaluate_impact_preview(db, preview_id=preview_id, actor=actor)
        db.commit()
        return row
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/signal-rule-impact-previews/{preview_id}/evaluations",
    response_model=list[SignalRuleImpactEvaluationOut],
)
def get_impact_preview_evaluations(
    preview_id: int,
    db: Session = Depends(get_db),
    limit: int = 50,
):
    return list_impact_evaluations(db, preview_id=preview_id, limit=limit)


@router.get(
    "/signal-rule-impact-evaluations/{evaluation_id}",
    response_model=SignalRuleImpactEvaluationOut,
)
def get_impact_evaluation_item(
    evaluation_id: int,
    db: Session = Depends(get_db),
) -> SignalRuleImpactEvaluation:
    row = get_impact_evaluation(db, evaluation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Impact evaluation not found")
    return row


@router.get("/signal-rules/impact-accuracy-leaderboard", response_model=RuleAccuracyLeaderboardResponse)
def get_impact_accuracy_leaderboard(
    db: Session = Depends(get_db),
    limit: int = 20,
) -> RuleAccuracyLeaderboardResponse:
    return {"items": impact_accuracy_leaderboard(db, limit=limit)}


@router.get("/signal-rules/{rule_id:int}/impact-accuracy-trend", response_model=RuleAccuracyTrendResponse)
def get_impact_accuracy_trend(
    rule_id: int,
    db: Session = Depends(get_db),
    window_size: int = 5,
    limit: int = 100,
) -> RuleAccuracyTrendResponse:
    try:
        return impact_accuracy_trend_for_rule(db, rule_id=rule_id, window_size=window_size, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/signal-rules/impact-accuracy-alerts", response_model=RuleAccuracyAlertsResponse)
def get_impact_accuracy_alerts(
    db: Session = Depends(get_db),
    min_evaluations: int = 3,
    error_threshold: float = 2.0,
    limit: int = 50,
) -> RuleAccuracyAlertsResponse:
    return {
        "items": detect_rule_accuracy_alerts(
            db,
            min_evaluations=min_evaluations,
            error_threshold=error_threshold,
            limit=limit,
        )
    }


@router.get("/candidates", response_model=list[CandidateOut])
def get_candidates(
    db: Session = Depends(get_db), status: str | None = Query(default=None), limit: int = 100
) -> list:
    return list_candidates(db, status=status, limit=limit)


@router.get("/candidates/{candidate_id}", response_model=CandidateOut)
def get_candidate_by_id(candidate_id: int, db: Session = Depends(get_db)):
    row = get_candidate(db, candidate_id)
    if not row:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return row


@router.post("/candidates/run")
def post_candidates_run(
    db: Session = Depends(get_db), limit_series: int = 200, _auth=require_role("editor")
) -> dict[str, int]:
    payload = run_signal_pipeline(db, limit_series=limit_series)
    db.commit()
    return payload


@router.post("/candidates/{candidate_id}/score", response_model=ScoreOut)
def post_candidate_score(candidate_id: int, db: Session = Depends(get_db), _auth=require_role("editor")):
    try:
        score_candidate(db, candidate_id)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    row = db.scalar(select(CandidateScore).where(CandidateScore.candidate_id == candidate_id))
    if not row:
        raise HTTPException(status_code=500, detail="Score computation failed")
    return row


@router.post("/candidates/{candidate_id}/draft", response_model=DraftOut)
def post_candidate_draft(candidate_id: int, db: Session = Depends(get_db), _auth=require_role("editor")):
    try:
        draft_candidate(db, candidate_id)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    row = db.scalar(select(CandidateDraft).where(CandidateDraft.candidate_id == candidate_id))
    if not row:
        raise HTTPException(status_code=500, detail="Draft generation failed")
    return row


@router.post("/candidates/{candidate_id}/crosses")
def post_candidate_crosses(
    candidate_id: int, db: Session = Depends(get_db), _auth=require_role("editor")
) -> CandidateCrossesResponse:
    try:
        crosses = suggest_candidate_crosses(db, candidate_id)
        db.commit()
        return {"candidate_id": candidate_id, "crosses": crosses}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/candidates/{candidate_id}/approve", response_model=CandidateOut)
def approve_candidate(
    candidate_id: int, db: Session = Depends(get_db), reviewer: str | None = None, _auth=require_role("editor")
):
    try:
        candidate = set_candidate_state(db, candidate_id, "accepted", reviewer=reviewer)
        db.commit()
        return candidate
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/candidates/{candidate_id}/discard", response_model=CandidateOut)
def discard_candidate(
    candidate_id: int, db: Session = Depends(get_db), reviewer: str | None = None, _auth=require_role("editor")
):
    try:
        candidate = set_candidate_state(db, candidate_id, "discarded", reviewer=reviewer)
        db.commit()
        return candidate
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/candidates/{candidate_id}/shortlist", response_model=CandidateOut)
def shortlist_candidate(
    candidate_id: int, db: Session = Depends(get_db), reviewer: str | None = None, _auth=require_role("editor")
):
    try:
        candidate = set_candidate_state(db, candidate_id, "shortlisted", reviewer=reviewer)
        db.commit()
        return candidate
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/candidates/{candidate_id}/publish",
    response_model=PublishPublicStoryResponse,
    summary="Publicar historia en la fachada web",
    description="Crea o actualiza `public_stories` a partir de un candidato aceptado, sin mutar el candidato.",
)
def post_publish_public_story(
    candidate_id: int,
    payload: PublishCandidatePayload,
    db: Session = Depends(get_db),
    _auth=require_role("editor"),
    actor: str | None = None,
) -> PublishPublicStoryResponse:
    try:
        row = publish_candidate(db, candidate_id, payload, actor=actor)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PublishPublicStoryResponse(
        public_story_id=row.id,
        slug=row.slug,
        status=row.status,
        published_at=row.published_at,
        scheduled_at=row.scheduled_at,
    )


@router.post("/candidates/{candidate_id}/send-to-cms", response_model=SendToCmsResponse)
def send_candidate_to_cms(
    candidate_id: int,
    target: str = Query(default="internal"),
    db: Session = Depends(get_db),
    _auth=require_role("editor"),
) -> SendToCmsResponse:
    try:
        row = send_to_publication_target(db, candidate_id, target)
        db.commit()
        return {"published_story_id": row.id, "status": row.status, "target_id": row.target_id}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/editorial/queue", response_model=list[CandidateOut])
def get_editorial_queue(db: Session = Depends(get_db), limit: int = 100):
    return list_queue(db, limit=limit)


@router.get("/editorial/dashboard", response_model=DashboardOverviewResponse)
def get_editorial_dashboard(db: Session = Depends(get_db)) -> DashboardOverviewResponse:
    return dashboard_stats(db)


@router.get("/editorial/dashboard/full", response_model=DashboardFullResponse)
def get_editorial_dashboard_full(
    db: Session = Depends(get_db),
    recent_limit: int = 10,
) -> DashboardFullResponse:
    return editorial_full_dashboard(db, recent_limit=recent_limit)


@router.get("/published", response_model=list[PublishedStoryOut])
def get_published(db: Session = Depends(get_db), limit: int = 100) -> list[PublishedStory]:
    return list(db.scalars(select(PublishedStory).order_by(PublishedStory.id.desc()).limit(limit)).all())


@router.get("/published/{published_id}", response_model=PublishedStoryOut)
def get_published_by_id(published_id: int, db: Session = Depends(get_db)) -> PublishedStory:
    row = db.get(PublishedStory, published_id)
    if not row:
        raise HTTPException(status_code=404, detail="Published story not found")
    return row
