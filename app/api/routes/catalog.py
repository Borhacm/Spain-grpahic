from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Dataset, Series, SeriesObservation, Source
from app.schemas import DatasetOut, SeriesObservationOut, SeriesOut, SourceOut

router = APIRouter(tags=["catalog"])


@router.get("/sources", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)) -> list[Source]:
    return list(db.scalars(select(Source).order_by(Source.slug)).all())


@router.get("/datasets", response_model=list[DatasetOut])
def list_datasets(
    db: Session = Depends(get_db), topic: str | None = Query(default=None), limit: int = 100
) -> list[Dataset]:
    stmt = select(Dataset).order_by(Dataset.id.desc()).limit(limit)
    if topic:
        stmt = stmt.where(Dataset.topic.ilike(f"%{topic}%"))
    return list(db.scalars(stmt).all())


@router.get("/datasets/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)) -> Dataset:
    row = db.get(Dataset, dataset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return row


@router.get("/series", response_model=list[SeriesOut])
def list_series(db: Session = Depends(get_db), limit: int = 100) -> list[Series]:
    return list(db.scalars(select(Series).order_by(Series.id.desc()).limit(limit)).all())


@router.get("/series/{series_id}", response_model=SeriesOut)
def get_series(series_id: int, db: Session = Depends(get_db)) -> Series:
    row = db.get(Series, series_id)
    if not row:
        raise HTTPException(status_code=404, detail="Series not found")
    return row


@router.get("/series/{series_id}/observations", response_model=list[SeriesObservationOut])
def get_observations(series_id: int, db: Session = Depends(get_db), limit: int = 200) -> list[SeriesObservation]:
    return list(
        db.scalars(
            select(SeriesObservation)
            .where(SeriesObservation.series_id == series_id)
            .order_by(SeriesObservation.obs_date.desc())
            .limit(limit)
        ).all()
    )
