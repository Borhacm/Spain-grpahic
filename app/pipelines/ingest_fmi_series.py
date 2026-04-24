from __future__ import annotations

from datetime import datetime

from app.connectors.fmi.connector import FMIConnector
from app.db.session import SessionLocal
from app.services.ingest import ensure_source, finish_run, insert_observation, start_run, upsert_series
from app.utils.normalization import to_decimal


def _parse_fmi_date(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
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


async def run(code: str, country: str = "ESP", dry_run: bool = False) -> dict[str, object]:
    db = SessionLocal()
    connector = FMIConnector()
    fetched = inserted = updated = failed = 0
    try:
        source = ensure_source(db, "fmi", "Fondo Monetario Internacional", connector.base_url)
        source_run = start_run(db, source.id, "ingest_fmi_series", dry_run)
        rows = await connector.fetch(code=code, country=country)
        series = upsert_series(
            db,
            source_id=source.id,
            external_code=f"{country.upper()}:{code.upper()}",
            name=f"FMI {country.upper()} - {code.upper()}",
            description="IMF DataMapper series",
            frequency="annual",
            unit="percent",
            source_url=f"{connector.base_url}/{code.upper()}/{country.upper()}",
            raw={"code": code.upper(), "country": country.upper()},
        )
        for row in rows:
            fetched += 1
            try:
                dt = _parse_fmi_date(row.get("TIME_PERIOD"))
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
