from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation


FREQUENCY_MAP: dict[str, str] = {
    "A": "annual",
    "Y": "annual",
    "Q": "quarterly",
    "M": "monthly",
    "D": "daily",
}


def to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def normalize_frequency(value: str | None) -> str | None:
    if not value:
        return None
    val = value.strip().upper()
    return FREQUENCY_MAP.get(val, value.lower())


def to_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
