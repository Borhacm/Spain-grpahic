from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import SeriesObservation


async def run(dry_run: bool = False) -> dict[str, object]:
    """
    Deduplicate historical observations for the base (revision_date is NULL) slice.

    Rule:
    - For each (series_id, obs_date) with revision_date=NULL and count > 1,
      keep the newest row (max id) and delete older duplicates.
    """
    db = SessionLocal()
    try:
        duplicate_groups = db.execute(
            select(
                SeriesObservation.series_id,
                SeriesObservation.obs_date,
                func.count(SeriesObservation.id).label("row_count"),
            )
            .where(SeriesObservation.revision_date.is_(None))
            .group_by(SeriesObservation.series_id, SeriesObservation.obs_date)
            .having(func.count(SeriesObservation.id) > 1)
        ).all()

        groups_processed = len(duplicate_groups)
        ids_to_delete: list[int] = []
        deleted_by_series: dict[int, int] = defaultdict(int)

        for series_id, obs_date, _ in duplicate_groups:
            rows = list(
                db.scalars(
                    select(SeriesObservation)
                    .where(
                        SeriesObservation.series_id == series_id,
                        SeriesObservation.obs_date == obs_date,
                        SeriesObservation.revision_date.is_(None),
                    )
                    .order_by(SeriesObservation.id.desc())
                ).all()
            )
            if len(rows) <= 1:
                continue
            duplicate_ids = [row.id for row in rows[1:]]
            ids_to_delete.extend(duplicate_ids)
            deleted_by_series[int(series_id)] += len(duplicate_ids)

        deleted_rows = len(ids_to_delete)
        if not dry_run and ids_to_delete:
            db.query(SeriesObservation).filter(SeriesObservation.id.in_(ids_to_delete)).delete(
                synchronize_session=False
            )
            db.commit()
        else:
            db.rollback()

        return {
            "dry_run": dry_run,
            "groups_processed": groups_processed,
            "rows_to_delete": deleted_rows,
            "deleted_by_series": dict(deleted_by_series),
        }
    finally:
        db.close()
