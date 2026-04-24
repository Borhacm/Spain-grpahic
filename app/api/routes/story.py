from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ArticleChartSpec, Company, SeriesObservation
from app.schemas import StorySeriesSummaryOut
from app.services.story import get_latest_observation, summarize_series

router = APIRouter(prefix="/story", tags=["story"])


@router.get("/series/{series_id}/latest")
def story_latest(series_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    latest = get_latest_observation(db, series_id)
    if not latest:
        raise HTTPException(status_code=404, detail="No observations found")
    return {
        "series_id": latest.series_id,
        "latest_date": latest.obs_date,
        "latest_value": latest.obs_value,
    }


@router.get("/series/{series_id}/summary", response_model=StorySeriesSummaryOut)
def story_summary(series_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        return summarize_series(db, series_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/series/{series_id}/compare")
def story_compare(
    series_id: int,
    geo: str = Query(default="ES"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    rows = db.scalars(
        select(SeriesObservation)
        .where(SeriesObservation.series_id == series_id)
        .order_by(SeriesObservation.obs_date.desc())
        .limit(12)
    ).all()
    return {"series_id": series_id, "geo": geo, "points": [r.obs_value for r in rows]}


@router.get("/rankings/companies")
def rankings_companies(
    metric: str = Query(default="filings_count"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if metric != "filings_count":
        return {"metric": metric, "items": []}
    rows = db.execute(
        select(Company.id, Company.canonical_name, func.count().label("value"))
        .join_from(Company, Company.filings)
        .group_by(Company.id)
        .order_by(desc("value"))
        .limit(20)
    ).all()
    return {
        "metric": metric,
        "items": [{"company_id": r.id, "company_name": r.canonical_name, "value": r.value} for r in rows],
    }


@router.get("/explore")
def story_explore(topic: str = Query(default="economia"), db: Session = Depends(get_db)) -> dict[str, object]:
    series_count = db.scalar(select(func.count()).select_from(SeriesObservation)) or Decimal(0)
    return {"topic": topic, "signals": [{"label": "series_observations", "value": int(series_count)}]}


@router.get("/chart/{chart_id}/spec")
def chart_spec(chart_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    spec = db.get(ArticleChartSpec, chart_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Chart spec not found")
    return {"id": spec.id, "chart_key": spec.chart_key, "spec": spec.spec_json}
