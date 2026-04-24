from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import Series, SeriesObservation


def get_latest_observation(db: Session, series_id: int) -> SeriesObservation | None:
    stmt: Select[tuple[SeriesObservation]] = (
        select(SeriesObservation)
        .where(SeriesObservation.series_id == series_id)
        .order_by(SeriesObservation.obs_date.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def _pct_change(new: Decimal | None, old: Decimal | None) -> Decimal | None:
    if new is None or old is None or old == 0:
        return None
    return ((new - old) / old) * Decimal(100)


def summarize_series(db: Session, series_id: int) -> dict[str, object]:
    series = db.get(Series, series_id)
    if not series:
        raise ValueError("Series not found")

    obs = db.scalars(
        select(SeriesObservation)
        .where(SeriesObservation.series_id == series_id)
        .order_by(SeriesObservation.obs_date.asc())
    ).all()
    if not obs:
        return {
            "series_id": series_id,
            "series_name": series.name,
            "latest_value": None,
            "latest_date": None,
            "yoy_change_pct": None,
            "cumulative_change_pct": None,
            "min_value": None,
            "max_value": None,
            "generated_text": f"La serie {series.name} no tiene observaciones disponibles.",
        }

    latest = obs[-1]
    first = obs[0]
    min_v, max_v = db.execute(
        select(func.min(SeriesObservation.obs_value), func.max(SeriesObservation.obs_value)).where(
            SeriesObservation.series_id == series_id
        )
    ).one()

    yoy_date = date(latest.obs_date.year - 1, latest.obs_date.month, 1)
    yoy_obs = db.scalar(
        select(SeriesObservation)
        .where(SeriesObservation.series_id == series_id, SeriesObservation.obs_date >= yoy_date)
        .order_by(SeriesObservation.obs_date.asc())
        .limit(1)
    )

    yoy = _pct_change(latest.obs_value, yoy_obs.obs_value if yoy_obs else None)
    cumulative = _pct_change(latest.obs_value, first.obs_value)
    generated = (
        f"La serie {series.name} cerró en {latest.obs_value} el {latest.obs_date.isoformat()}, "
        f"un cambio de {round(yoy, 2) if yoy is not None else 'N/D'}% interanual."
    )
    return {
        "series_id": series.id,
        "series_name": series.name,
        "latest_value": latest.obs_value,
        "latest_date": latest.obs_date,
        "yoy_change_pct": yoy,
        "cumulative_change_pct": cumulative,
        "min_value": min_v,
        "max_value": max_v,
        "generated_text": generated,
    }
