from __future__ import annotations

from sqlalchemy import select

from app.core.job_lock import advisory_job_lock
from app.db.session import SessionLocal
from app.editorial.models import StoryCandidate
from app.editorial.repositories.candidates import set_candidate_status
from app.editorial.services.candidate_service import (
    draft_candidate,
    run_signal_pipeline,
    score_candidate,
    suggest_candidate_crosses,
)
from app.editorial.services.rule_service import detect_rule_accuracy_alerts
from app.pipelines.maintenance_dedupe_observations import run as dedupe_observations


async def detect_daily_signals(dry_run: bool = False) -> dict[str, object]:
    db = SessionLocal()
    try:
        with advisory_job_lock(db, "detect_daily_signals") as locked:
            if not locked:
                return {
                    "job": "detect_daily_signals",
                    "dry_run": dry_run,
                    "skipped": "lock_not_acquired",
                }
            result = run_signal_pipeline(db, limit_series=200)
        if not dry_run:
            db.commit()
        else:
            db.rollback()
        return {"job": "detect_daily_signals", "dry_run": dry_run, **result}
    finally:
        db.close()


async def maintenance_dedupe_observations_job(dry_run: bool = False) -> dict[str, object]:
    """
    Weekly safety net: remove duplicate base observations (revision_date NULL).
    Uses advisory lock so only one replica runs it at a time.
    """
    db = SessionLocal()
    try:
        with advisory_job_lock(db, "maintenance_dedupe_observations") as locked:
            if not locked:
                return {
                    "job": "maintenance_dedupe_observations",
                    "dry_run": dry_run,
                    "skipped": "lock_not_acquired",
                }
            result = await dedupe_observations(dry_run=dry_run)
        return {"job": "maintenance_dedupe_observations", **result}
    finally:
        db.close()


async def detect_weekly_signals(dry_run: bool = False) -> dict[str, object]:
    db = SessionLocal()
    try:
        with advisory_job_lock(db, "detect_weekly_signals") as locked:
            if not locked:
                return {
                    "job": "detect_weekly_signals",
                    "dry_run": dry_run,
                    "skipped": "lock_not_acquired",
                }
            result = run_signal_pipeline(db, limit_series=500)
        if not dry_run:
            db.commit()
        else:
            db.rollback()
        return {"job": "detect_weekly_signals", "dry_run": dry_run, **result}
    finally:
        db.close()


async def refresh_scores(dry_run: bool = False) -> dict[str, object]:
    db = SessionLocal()
    processed = 0
    try:
        with advisory_job_lock(db, "refresh_scores") as locked:
            if not locked:
                return {
                    "job": "refresh_scores",
                    "processed": processed,
                    "dry_run": dry_run,
                    "skipped": "lock_not_acquired",
                }
            ids = list(db.scalars(select(StoryCandidate.id)).all())
            for candidate_id in ids:
                score_candidate(db, candidate_id)
                processed += 1
        if not dry_run:
            db.commit()
        else:
            db.rollback()
        return {"job": "refresh_scores", "processed": processed, "dry_run": dry_run}
    finally:
        db.close()


async def generate_candidate_drafts(dry_run: bool = False) -> dict[str, object]:
    db = SessionLocal()
    processed = 0
    try:
        with advisory_job_lock(db, "generate_candidate_drafts") as locked:
            if not locked:
                return {
                    "job": "generate_candidate_drafts",
                    "processed": processed,
                    "dry_run": dry_run,
                    "skipped": "lock_not_acquired",
                }
            candidates = db.scalars(select(StoryCandidate)).all()
            for candidate in candidates:
                draft_candidate(db, candidate.id)
                processed += 1
        if not dry_run:
            db.commit()
        else:
            db.rollback()
        return {"job": "generate_candidate_drafts", "processed": processed, "dry_run": dry_run}
    finally:
        db.close()


async def suggest_crosses(dry_run: bool = False) -> dict[str, object]:
    db = SessionLocal()
    processed = 0
    try:
        with advisory_job_lock(db, "suggest_crosses") as locked:
            if not locked:
                return {
                    "job": "suggest_crosses",
                    "processed": processed,
                    "dry_run": dry_run,
                    "skipped": "lock_not_acquired",
                }
            candidates = db.scalars(select(StoryCandidate)).all()
            for candidate in candidates:
                suggest_candidate_crosses(db, candidate.id)
                processed += 1
        if not dry_run:
            db.commit()
        else:
            db.rollback()
        return {"job": "suggest_crosses", "processed": processed, "dry_run": dry_run}
    finally:
        db.close()


async def archive_low_score_candidates(dry_run: bool = False) -> dict[str, object]:
    db = SessionLocal()
    archived = 0
    try:
        with advisory_job_lock(db, "archive_low_score_candidates") as locked:
            if not locked:
                return {
                    "job": "archive_low_score_candidates",
                    "archived": archived,
                    "dry_run": dry_run,
                    "skipped": "lock_not_acquired",
                }
            candidates = db.scalars(
                select(StoryCandidate).where(StoryCandidate.score_total < 2)
            ).all()
            for candidate in candidates:
                set_candidate_status(candidate, "archived")
                archived += 1
        if not dry_run:
            db.commit()
        else:
            db.rollback()
        return {"job": "archive_low_score_candidates", "archived": archived, "dry_run": dry_run}
    finally:
        db.close()


async def evaluate_rule_accuracy_alerts(dry_run: bool = False) -> dict[str, object]:
    db = SessionLocal()
    try:
        with advisory_job_lock(db, "evaluate_rule_accuracy_alerts") as locked:
            if not locked:
                return {
                    "job": "evaluate_rule_accuracy_alerts",
                    "dry_run": dry_run,
                    "skipped": "lock_not_acquired",
                }
            alerts = detect_rule_accuracy_alerts(
                db,
                min_evaluations=3,
                error_threshold=2.0,
                limit=100,
            )
        if dry_run:
            db.rollback()
        else:
            db.commit()
        return {
            "job": "evaluate_rule_accuracy_alerts",
            "dry_run": dry_run,
            "alerts_count": len(alerts),
            "alerts": alerts[:20],
        }
    finally:
        db.close()
