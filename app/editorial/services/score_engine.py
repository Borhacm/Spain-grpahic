from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.editorial.models import CandidateSignal, SignalRule, StoryCandidate


DEFAULT_WEIGHTS: dict[str, Decimal] = {
    "novelty": Decimal("0.2"),
    "magnitude": Decimal("0.25"),
    "freshness": Decimal("0.15"),
    "editorial": Decimal("0.15"),
    "clarity": Decimal("0.1"),
    "robustness": Decimal("0.15"),
}


def _clamp(value: Decimal, low: Decimal = Decimal("0"), high: Decimal = Decimal("10")) -> Decimal:
    return min(max(value, low), high)


def compute_candidate_score(db: Session, candidate_id: int) -> tuple[dict[str, Decimal], str]:
    candidate = db.get(StoryCandidate, candidate_id)
    if not candidate:
        raise ValueError("Candidate not found")
    signals = list(db.scalars(select(CandidateSignal).where(CandidateSignal.candidate_id == candidate_id)).all())
    signal_strength = max([s.strength for s in signals], default=Decimal("0"))
    novelty = _clamp(Decimal("4") + (Decimal("2") if len(signals) > 1 else Decimal("0")))
    magnitude = _clamp(signal_strength / Decimal("2"))
    created_at = candidate.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    freshness = _clamp(Decimal("10") if (datetime.now(UTC) - created_at).days <= 2 else Decimal("6"))
    editorial = _clamp(Decimal("7") if candidate.why_it_matters else Decimal("4"))
    clarity = _clamp(Decimal("7") if candidate.executive_summary else Decimal("5"))
    robustness = _clamp(Decimal("8") if len(signals) >= 2 else Decimal("5"))
    noise_penalty = _clamp(Decimal("1") if signal_strength < Decimal("4") else Decimal("0"))

    rules = list(db.scalars(select(SignalRule).where(SignalRule.enabled.is_(True))).all())
    weight_boost = sum([rule.weight for rule in rules], start=Decimal("0")) / Decimal("100")

    total = (
        novelty * DEFAULT_WEIGHTS["novelty"]
        + magnitude * DEFAULT_WEIGHTS["magnitude"]
        + freshness * DEFAULT_WEIGHTS["freshness"]
        + editorial * DEFAULT_WEIGHTS["editorial"]
        + clarity * DEFAULT_WEIGHTS["clarity"]
        + robustness * DEFAULT_WEIGHTS["robustness"]
    ) - noise_penalty + weight_boost
    total = _clamp(total, Decimal("0"), Decimal("10"))
    rationale = (
        f"Score basado en {len(signals)} señales; magnitud={magnitude}, freshness={freshness}, "
        f"noise_penalty={noise_penalty}, rule_boost={weight_boost:.2f}."
    )
    return (
        {
            "novelty_score": novelty,
            "magnitude_score": magnitude,
            "freshness_score": freshness,
            "editorial_score": editorial,
            "clarity_score": clarity,
            "robustness_score": robustness,
            "noise_penalty": noise_penalty,
            "total_score": total,
        },
        rationale,
    )
