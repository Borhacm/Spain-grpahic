from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings

_scheduler: AsyncIOScheduler | None = None
_logger = logging.getLogger(__name__)


def _job_wrapper(coro_func):
    async def _run():
        await coro_func(dry_run=False)

    return _run


def _schedule_task(coro_func):
    return lambda: asyncio.create_task(coro_func())


def _cron_trigger(expr: str, *, fallback_hour: int, fallback_minute: int, day_of_week: str | None = None) -> CronTrigger:
    try:
        return CronTrigger.from_crontab(expr)
    except Exception:
        _logger.warning("Invalid cron expression '%s', using fallback.", expr)
        return CronTrigger(hour=fallback_hour, minute=fallback_minute, day_of_week=day_of_week)


async def _ingest_ine_job() -> None:
    from app.pipelines.ingest_ine_series import run as ingest_ine_series

    await ingest_ine_series(dry_run=False)


async def _ingest_bde_job() -> None:
    from app.pipelines.ingest_bde_series import run as ingest_bde_series

    settings = get_settings()
    codes = [code.strip() for code in settings.scheduler_bde_codes.split(",") if code.strip()]
    if not codes:
        _logger.info("Skipping scheduled BDE ingest: SCHEDULER_BDE_CODES is empty.")
        return
    for code in codes:
        await ingest_bde_series(code=code, dry_run=False)


async def _ingest_oecd_job() -> None:
    from app.pipelines.ingest_oecd_series import run as ingest_oecd_series

    settings = get_settings()
    codes = [code.strip() for code in settings.scheduler_oecd_codes.split(",") if code.strip()]
    if not codes:
        _logger.info("Skipping scheduled OECD ingest: SCHEDULER_OECD_CODES is empty.")
        return
    for code in codes:
        await ingest_oecd_series(code=code, dry_run=False)


async def _ingest_fmi_job() -> None:
    from app.pipelines.ingest_fmi_series import run as ingest_fmi_series

    settings = get_settings()
    codes = [code.strip() for code in settings.scheduler_fmi_codes.split(",") if code.strip()]
    if not codes:
        _logger.info("Skipping scheduled FMI ingest: SCHEDULER_FMI_CODES is empty.")
        return
    for code in codes:
        await ingest_fmi_series(code=code, country="ESP", dry_run=False)


def start_scheduler() -> AsyncIOScheduler | None:
    global _scheduler
    settings = get_settings()
    if not settings.scheduler_enabled:
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    # Lazy import avoids circular import during app/module initialization.
    from app.editorial.tasks.jobs import (
        detect_daily_signals,
        detect_weekly_signals,
        maintenance_dedupe_observations_job,
        refresh_scores,
    )

    scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
    scheduler.add_job(
        _schedule_task(_job_wrapper(detect_daily_signals)),
        CronTrigger(hour=7, minute=5),
        id="detect_daily_signals",
        max_instances=1,
        replace_existing=True,
        coalesce=True,
    )
    scheduler.add_job(
        _schedule_task(_job_wrapper(refresh_scores)),
        CronTrigger(hour=7, minute=20),
        id="refresh_scores",
        max_instances=1,
        replace_existing=True,
        coalesce=True,
    )
    scheduler.add_job(
        _schedule_task(_job_wrapper(detect_weekly_signals)),
        CronTrigger(day_of_week="mon", hour=7, minute=30),
        id="detect_weekly_signals",
        max_instances=1,
        replace_existing=True,
        coalesce=True,
    )
    scheduler.add_job(
        _schedule_task(_job_wrapper(maintenance_dedupe_observations_job)),
        CronTrigger(day_of_week="sun", hour=3, minute=15),
        id="maintenance_dedupe_observations",
        max_instances=1,
        replace_existing=True,
        coalesce=True,
    )
    if settings.scheduler_ingest_ine_enabled:
        scheduler.add_job(
            _schedule_task(_ingest_ine_job),
            _cron_trigger(settings.scheduler_ingest_ine_cron, fallback_hour=6, fallback_minute=15),
            id="ingest_ine_series",
            max_instances=1,
            replace_existing=True,
            coalesce=True,
        )
    if settings.scheduler_ingest_bde_enabled:
        scheduler.add_job(
            _schedule_task(_ingest_bde_job),
            _cron_trigger(settings.scheduler_ingest_bde_cron, fallback_hour=6, fallback_minute=45),
            id="ingest_bde_series",
            max_instances=1,
            replace_existing=True,
            coalesce=True,
        )
    if settings.scheduler_ingest_oecd_enabled:
        scheduler.add_job(
            _schedule_task(_ingest_oecd_job),
            _cron_trigger(settings.scheduler_ingest_oecd_cron, fallback_hour=7, fallback_minute=30),
            id="ingest_oecd_series",
            max_instances=1,
            replace_existing=True,
            coalesce=True,
        )
    if settings.scheduler_ingest_fmi_enabled:
        scheduler.add_job(
            _schedule_task(_ingest_fmi_job),
            _cron_trigger(settings.scheduler_ingest_fmi_cron, fallback_hour=7, fallback_minute=40),
            id="ingest_fmi_series",
            max_instances=1,
            replace_existing=True,
            coalesce=True,
        )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None


def scheduler_status() -> dict[str, object]:
    if not _scheduler:
        return {"enabled": False, "running": False, "jobs": []}
    jobs = [job.id for job in _scheduler.get_jobs()]
    return {"enabled": True, "running": bool(_scheduler.running), "jobs": jobs}
