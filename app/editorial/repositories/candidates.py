from __future__ import annotations

from difflib import SequenceMatcher
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.editorial.models import (
    CandidateCross,
    CandidateDraft,
    CandidateRelatedCompany,
    CandidateRelatedSeries,
    CandidateScore,
    CandidateSignal,
    EditorialReview,
    StoryCandidate,
)


def list_candidates(db: Session, status: str | None = None, limit: int = 100) -> list[StoryCandidate]:
    stmt = select(StoryCandidate).order_by(StoryCandidate.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(StoryCandidate.status == status)
    return list(db.scalars(stmt).all())


def get_candidate(db: Session, candidate_id: int) -> StoryCandidate | None:
    return db.get(StoryCandidate, candidate_id)


def get_candidate_by_hash(db: Session, dedupe_hash: str) -> StoryCandidate | None:
    return db.scalar(select(StoryCandidate).where(StoryCandidate.dedupe_hash == dedupe_hash))


def find_similar_candidate(
    db: Session,
    *,
    title: str,
    insight: str,
    geography: str | None,
    period_label: str | None,
    threshold: float = 0.9,
) -> StoryCandidate | None:
    candidates = list(
        db.scalars(select(StoryCandidate).order_by(StoryCandidate.created_at.desc()).limit(300)).all()
    )
    baseline = f"{title.strip().lower()}|{insight.strip().lower()}"
    for candidate in candidates:
        if geography and candidate.geography and geography != candidate.geography:
            continue
        if period_label and candidate.period_label and period_label != candidate.period_label:
            continue
        probe = f"{candidate.title.strip().lower()}|{candidate.insight.strip().lower()}"
        ratio = SequenceMatcher(a=baseline, b=probe).ratio()
        if ratio >= threshold:
            return candidate
    return None


def create_or_get_candidate(
    db: Session,
    *,
    dedupe_hash: str,
    title: str,
    insight: str,
    executive_summary: str | None,
    why_it_matters: str | None,
    geography: str | None,
    period_label: str | None,
) -> StoryCandidate:
    existing = db.scalar(select(StoryCandidate).where(StoryCandidate.dedupe_hash == dedupe_hash))
    if existing:
        existing.updated_at = datetime.now(UTC)
        return existing
    candidate = StoryCandidate(
        dedupe_hash=dedupe_hash,
        title=title,
        insight=insight,
        executive_summary=executive_summary,
        why_it_matters=why_it_matters,
        geography=geography,
        period_label=period_label,
        status="new",
    )
    db.add(candidate)
    db.flush()
    return candidate


def set_candidate_status(candidate: StoryCandidate, status: str) -> None:
    candidate.status = status


def add_signal(
    db: Session,
    candidate_id: int,
    signal_type: str,
    signal_key: str,
    explanation: str,
    strength: Decimal,
    rule_id: int | None = None,
    payload_json: dict[str, object] | None = None,
) -> CandidateSignal:
    existing = db.scalar(
        select(CandidateSignal).where(
            CandidateSignal.candidate_id == candidate_id,
            CandidateSignal.signal_key == signal_key,
        )
    )
    if existing:
        existing.signal_type = signal_type
        existing.explanation = explanation
        existing.strength = strength
        existing.rule_id = rule_id
        existing.payload_json = payload_json
        db.flush()
        return existing
    signal = CandidateSignal(
        candidate_id=candidate_id,
        signal_type=signal_type,
        signal_key=signal_key,
        explanation=explanation,
        strength=strength,
        rule_id=rule_id,
        payload_json=payload_json,
    )
    db.add(signal)
    db.flush()
    return signal


def upsert_score(db: Session, candidate_id: int, values: dict[str, Decimal], rationale: str) -> CandidateScore:
    row = db.scalar(select(CandidateScore).where(CandidateScore.candidate_id == candidate_id))
    if row is None:
        row = CandidateScore(candidate_id=candidate_id, rationale=rationale, **values)
        db.add(row)
    else:
        for k, v in values.items():
            setattr(row, k, v)
        row.rationale = rationale
    candidate = db.get(StoryCandidate, candidate_id)
    if candidate:
        candidate.score_total = values["total_score"]
        candidate.updated_at = datetime.now(UTC)
    db.flush()
    return row


def upsert_draft(db: Session, candidate_id: int, payload: dict[str, object]) -> CandidateDraft:
    row = db.scalar(select(CandidateDraft).where(CandidateDraft.candidate_id == candidate_id))
    if row is None:
        row = CandidateDraft(candidate_id=candidate_id, **payload)
        db.add(row)
    else:
        for k, v in payload.items():
            setattr(row, k, v)
    db.flush()
    return row


def replace_crosses(db: Session, candidate_id: int, crosses: list[dict[str, str]]) -> None:
    db.query(CandidateCross).filter(CandidateCross.candidate_id == candidate_id).delete()
    for item in crosses:
        db.add(
            CandidateCross(
                candidate_id=candidate_id,
                left_entity=item["left_entity"],
                right_entity=item["right_entity"],
                rationale=item["rationale"],
                suggested_angle=item["suggested_angle"],
                suggested_chart_type=item.get("suggested_chart_type"),
            )
        )


def set_related_series(db: Session, candidate_id: int, series_id: int) -> None:
    exists = db.scalar(
        select(CandidateRelatedSeries).where(
            CandidateRelatedSeries.candidate_id == candidate_id,
            CandidateRelatedSeries.series_id == series_id,
        )
    )
    if not exists:
        db.add(CandidateRelatedSeries(candidate_id=candidate_id, series_id=series_id, relation_type="primary"))


def set_related_company(db: Session, candidate_id: int, company_id: int) -> None:
    exists = db.scalar(
        select(CandidateRelatedCompany).where(
            CandidateRelatedCompany.candidate_id == candidate_id,
            CandidateRelatedCompany.company_id == company_id,
        )
    )
    if not exists:
        db.add(
            CandidateRelatedCompany(
                candidate_id=candidate_id, company_id=company_id, relation_type="mentioned"
            )
        )


def review_action(
    db: Session,
    candidate_id: int,
    action: str,
    reviewer: str | None = None,
    notes: str | None = None,
    metadata_json: dict[str, object] | None = None,
) -> None:
    db.add(
        EditorialReview(
            candidate_id=candidate_id,
            action=action,
            reviewer=reviewer,
            notes=notes,
            metadata_json=metadata_json,
        )
    )
