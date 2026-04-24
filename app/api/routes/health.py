from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.job_lock import advisory_job_lock, lock_backend
from app.core.scheduler import scheduler_status
from app.db.session import get_db
from app.models import Source, SourceRun

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def healthcheck(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/sources")
def health_sources(db: Session = Depends(get_db)) -> dict[str, object]:
    rows = db.query(Source).all()
    return {
        "status": "ok",
        "sources": [{"slug": s.slug, "enabled": s.enabled} for s in rows],
    }


@router.get("/ops")
def health_ops(db: Session = Depends(get_db)) -> dict[str, object]:
    scheduler = scheduler_status()
    lock_probe = False
    with advisory_job_lock(db, "health_ops_probe") as locked:
        lock_probe = locked
    return {
        "status": "ok",
        "scheduler": scheduler,
        "locking": {
            "backend": lock_backend(db),
            "probe_lock_acquired": lock_probe,
        },
    }


@router.get("/scheduler-runs")
def health_scheduler_runs(db: Session = Depends(get_db)) -> dict[str, object]:
    settings = get_settings()
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

    return {
        "status": "ok",
        "scheduler_expected_in_worker": settings.scheduler_enabled,
        "tracked_jobs": tracked_jobs,
        "latest_runs": [
            {
                "pipeline_name": job,
                "last_status": latest_by_job[job].status if job in latest_by_job else None,
                "last_started_at": (
                    latest_by_job[job].started_at.isoformat() if job in latest_by_job else None
                ),
                "last_finished_at": (
                    latest_by_job[job].finished_at.isoformat() if job in latest_by_job else None
                ),
                "items_fetched": latest_by_job[job].items_fetched if job in latest_by_job else None,
                "items_inserted": latest_by_job[job].items_inserted if job in latest_by_job else None,
                "items_failed": latest_by_job[job].items_failed if job in latest_by_job else None,
                "dry_run": latest_by_job[job].dry_run if job in latest_by_job else None,
            }
            for job in tracked_jobs
        ],
    }
