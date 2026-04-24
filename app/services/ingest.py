from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Dataset, DatasetResource, Series, SeriesObservation, Source, SourceRun
from app.utils.normalization import normalize_frequency, to_decimal


def ensure_source(db: Session, slug: str, name: str, base_url: str, source_type: str = "api") -> Source:
    source = db.scalar(select(Source).where(Source.slug == slug))
    if source:
        return source
    source = Source(slug=slug, name=name, base_url=base_url, source_type=source_type)
    db.add(source)
    db.flush()
    return source


def start_run(db: Session, source_id: int, pipeline_name: str, dry_run: bool) -> SourceRun:
    run = SourceRun(source_id=source_id, pipeline_name=pipeline_name, dry_run=dry_run, status="running")
    db.add(run)
    db.flush()
    return run


def finish_run(
    db: Session,
    run: SourceRun,
    status: str,
    fetched: int,
    inserted: int,
    updated: int,
    failed: int,
    error_summary: str | None = None,
) -> None:
    run.status = status
    run.finished_at = datetime.now(UTC)
    run.items_fetched = fetched
    run.items_inserted = inserted
    run.items_updated = updated
    run.items_failed = failed
    run.error_summary = error_summary


def upsert_dataset(
    db: Session, source_id: int, external_id: str, title: str, raw: dict[str, Any], **kwargs: Any
) -> tuple[Dataset, bool]:
    row = db.scalar(
        select(Dataset).where(Dataset.source_id == source_id, Dataset.external_id == external_id)
    )
    now = datetime.now(UTC)
    if row:
        row.title = title
        row.last_seen_at = now
        row.description = kwargs.get("description")
        row.topic = kwargs.get("topic")
        row.publisher = kwargs.get("publisher")
        row.geography_scope = kwargs.get("geography_scope")
        row.update_frequency = kwargs.get("update_frequency")
        row.license = kwargs.get("license")
        row.source_url = kwargs.get("source_url")
        row.raw_metadata_json = raw
        return row, False
    row = Dataset(
        source_id=source_id,
        external_id=external_id,
        title=title,
        description=kwargs.get("description"),
        topic=kwargs.get("topic"),
        publisher=kwargs.get("publisher"),
        geography_scope=kwargs.get("geography_scope"),
        update_frequency=kwargs.get("update_frequency"),
        license=kwargs.get("license"),
        source_url=kwargs.get("source_url"),
        raw_metadata_json=raw,
        first_seen_at=now,
        last_seen_at=now,
    )
    db.add(row)
    db.flush()
    return row, True


def upsert_dataset_resource(
    db: Session, dataset_id: int, external_id: str | None, raw: dict[str, Any]
) -> None:
    if not external_id:
        return
    row = db.scalar(
        select(DatasetResource).where(
            DatasetResource.dataset_id == dataset_id, DatasetResource.external_id == external_id
        )
    )
    if row:
        row.title = raw.get("title")
        row.format = raw.get("format")
        row.download_url = raw.get("downloadURL")
        row.raw_metadata_json = raw
        return
    db.add(
        DatasetResource(
            dataset_id=dataset_id,
            external_id=external_id,
            title=raw.get("title"),
            format=raw.get("format"),
            download_url=raw.get("downloadURL"),
            raw_metadata_json=raw,
        )
    )


def upsert_series(
    db: Session, source_id: int, external_code: str, name: str, raw: dict[str, Any], **kwargs: Any
) -> Series:
    row = db.scalar(select(Series).where(Series.source_id == source_id, Series.external_code == external_code))
    if row:
        row.name = name
        row.description = kwargs.get("description")
        row.unit = kwargs.get("unit")
        row.frequency = normalize_frequency(kwargs.get("frequency"))
        row.source_url = kwargs.get("source_url")
        row.raw_metadata_json = raw
        return row
    row = Series(
        source_id=source_id,
        dataset_id=kwargs.get("dataset_id"),
        external_code=external_code,
        name=name,
        description=kwargs.get("description"),
        unit=kwargs.get("unit"),
        frequency=normalize_frequency(kwargs.get("frequency")),
        source_url=kwargs.get("source_url"),
        raw_metadata_json=raw,
    )
    db.add(row)
    db.flush()
    return row


def insert_observation(
    db: Session,
    series_id: int,
    obs_date: Any,
    obs_value: Any,
    raw_payload: dict[str, Any],
    obs_text: str | None = None,
) -> None:
    if not obs_date:
        return
    value = to_decimal(obs_value)
    existing = db.scalar(
        select(SeriesObservation).where(
            SeriesObservation.series_id == series_id,
            SeriesObservation.obs_date == obs_date,
            SeriesObservation.revision_date.is_(None),
        )
    )
    if existing:
        existing.obs_value = value
        existing.obs_text = obs_text
        existing.raw_payload_json = raw_payload
        return
    row = SeriesObservation(
        series_id=series_id,
        obs_date=obs_date,
        obs_value=value,
        obs_text=obs_text,
        raw_payload_json=raw_payload,
    )
    db.add(row)
