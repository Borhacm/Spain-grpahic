from __future__ import annotations

from sqlalchemy.orm import Session

from app.editorial.models import StoryCandidate
from app.editorial.repositories.candidates import review_action, set_candidate_status

VALID_STATES = {"new", "reviewing", "shortlisted", "accepted", "discarded", "published", "archived"}


def set_candidate_state(
    db: Session, candidate_id: int, state: str, reviewer: str | None = None, notes: str | None = None
) -> StoryCandidate:
    # Backward-compatible naming: "state" argument maps to StoryCandidate.status.
    if state not in VALID_STATES:
        raise ValueError(f"Invalid state: {state}")
    candidate = db.get(StoryCandidate, candidate_id)
    if not candidate:
        raise ValueError("Candidate not found")
    set_candidate_status(candidate, state)
    review_action(db, candidate_id, action=state, reviewer=reviewer, notes=notes)
    db.flush()
    return candidate
