from __future__ import annotations

from datetime import datetime

from app.connectors.oecd.connector import OECDConnector
from app.db.session import SessionLocal
from app.services.ingest import ensure_source, finish_run, insert_observation, start_run, upsert_series
from app.utils.normalization import to_decimal


def _parse_oecd_date(value: str | None, frequency: str | None = None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    if (frequency or "").upper() == "A":
        try:
            year = int(cleaned)
            return datetime(year, 1, 1)
        except ValueError:
            return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            dt = datetime.strptime(cleaned, fmt)
            if fmt == "%Y-%m":
                return datetime(dt.year, dt.month, 1)
            if fmt == "%Y":
                return datetime(dt.year, 1, 1)
            return dt
        except ValueError:
            continue
    return None


def _series_name_from_key(code: str) -> str:
    normalized = code.upper()
    if ".DG." in normalized or ":DG:" in normalized:
        return "OECD Digital Government Index (Spain)"
    if ".OUR." in normalized or ":OUR:" in normalized:
        return "OECD OURdata Index (Spain)"
    return f"OECD Series {code}"


async def run(code: str, dry_run: bool = False) -> dict[str, object]:
    db = SessionLocal()
    connector = OECDConnector()
    fetched = inserted = updated = failed = 0
    try:
        source = ensure_source(db, "oecd", "OECD", connector.base_url)
        source_run = start_run(db, source.id, "ingest_oecd_series", dry_run)
        rows = await connector.fetch(code=code)
        series_name = _series_name_from_key(code)
        series = upsert_series(
            db,
            source_id=source.id,
            external_code=code,
            name=series_name,
            description="OECD SDMX series",
            frequency="annual",
            unit="index",
            source_url=f"{connector.base_url}/{code}",
            raw={"code": code},
        )
        for row in rows:
            fetched += 1
            try:
                frequency = row.get("FREQ")
                dt = _parse_oecd_date(row.get("TIME_PERIOD"), frequency=frequency)
                if not dt:
                    continue
                insert_observation(
                    db,
                    series_id=series.id,
                    obs_date=dt.date(),
                    obs_value=to_decimal(row.get("OBS_VALUE")),
                    raw_payload=row,
                )
                inserted += 1
            except Exception:
                failed += 1
        if not dry_run:
            db.commit()
        finish_run(
            db, source_run, "partial" if failed else "success", fetched, inserted, updated, failed
        )
        db.commit()
        return {"fetched": fetched, "inserted": inserted, "updated": updated, "failed": failed}
    except Exception as exc:
        db.rollback()
        return {"status": "failed", "error": str(exc)}
    finally:
        await connector.close()
        db.close()
