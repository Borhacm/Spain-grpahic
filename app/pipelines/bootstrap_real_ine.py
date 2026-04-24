from __future__ import annotations

from app.db.session import SessionLocal
from app.editorial.repositories.candidates import list_candidates
from app.editorial.services.candidate_service import (
    draft_candidate,
    run_signal_pipeline,
    score_candidate,
    suggest_candidate_crosses,
)
from app.pipelines.ingest_ine_series import run as ingest_ine_series

DEFAULT_INE_CODES = ["CP335", "IPC206449", "EPA87", "EPA452434", "EPA77038"]


async def run(dry_run: bool = False) -> dict[str, object]:
    ingest_results: list[dict[str, object]] = []
    for code in DEFAULT_INE_CODES:
        payload = await ingest_ine_series(code=code, dry_run=dry_run)
        ingest_results.append({"code": code, "result": payload})

    if dry_run:
        return {"dry_run": True, "ingested": ingest_results}

    db = SessionLocal()
    try:
        signal_payload = run_signal_pipeline(db, limit_series=300)
        db.commit()

        candidates = list_candidates(db, limit=200)
        enriched = 0
        for candidate in candidates:
            score_candidate(db, candidate.id)
            draft_candidate(db, candidate.id)
            suggest_candidate_crosses(db, candidate.id)
            enriched += 1
        db.commit()

        return {
            "dry_run": False,
            "ingested": ingest_results,
            "signals": signal_payload,
            "candidates_enriched": enriched,
        }
    finally:
        db.close()
