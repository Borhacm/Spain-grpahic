from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SourceOut(ORMModel):
    id: int
    slug: str
    name: str
    source_type: str
    base_url: str | None
    auth_type: str | None
    enabled: bool


class DatasetOut(ORMModel):
    id: int
    source_id: int
    external_id: str
    title: str
    description: str | None
    topic: str | None
    publisher: str | None
    geography_scope: str | None
    update_frequency: str | None
    license: str | None
    source_url: str | None
    raw_metadata_json: dict[str, Any] | None
    first_seen_at: datetime
    last_seen_at: datetime


class SeriesOut(ORMModel):
    id: int
    dataset_id: int | None
    source_id: int
    external_code: str
    name: str
    description: str | None
    unit: str | None
    frequency: str | None
    source_url: str | None
    raw_metadata_json: dict[str, Any] | None


class SeriesObservationOut(ORMModel):
    id: int
    series_id: int
    obs_date: date
    obs_value: Decimal | None
    obs_text: str | None
    revision_date: date | None
    raw_payload_json: dict[str, Any] | None


class CompanyOut(ORMModel):
    id: int
    canonical_name: str
    legal_name: str | None
    country_code: str
    website: str | None
    company_type: str | None
    is_listed: bool


class CompanySnapshotOut(ORMModel):
    id: int
    company_id: int
    source_id: int
    snapshot_date: date
    status: str | None
    legal_form: str | None
    cnae: str | None
    nace: str | None
    province: str | None
    municipality: str | None
    address: str | None
    administrators_json: dict[str, Any] | None


class FilingOut(ORMModel):
    id: int
    company_id: int
    source_id: int
    filing_type: str
    filing_date: date | None
    period_start: date | None
    period_end: date | None
    title: str | None
    url: str | None


class StorySeriesSummaryOut(BaseModel):
    series_id: int
    series_name: str
    latest_value: Decimal | None
    latest_date: date | None
    yoy_change_pct: Decimal | None
    cumulative_change_pct: Decimal | None
    min_value: Decimal | None
    max_value: Decimal | None
    generated_text: str
