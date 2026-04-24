from __future__ import annotations

from datetime import datetime

from app.connectors.bde.connector import BDEConnector
from app.db.session import SessionLocal
from app.services.ingest import ensure_source, finish_run, insert_observation, start_run, upsert_series
from app.utils.normalization import to_decimal


def _parse_bde_date(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(cleaned)
        return datetime(dt.year, dt.month, 1)
    except ValueError:
        pass
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


async def run(code: str, dry_run: bool = False) -> dict[str, object]:
    db = SessionLocal()
    connector = BDEConnector()
    fetched = inserted = updated = failed = 0
    try:
        source = ensure_source(db, "bde", "Banco de Espana", connector.base_url)
        source_run = start_run(db, source.id, "ingest_bde_series", dry_run)
        rows = await connector.fetch(code=code)
        serie = upsert_series(
            db,
            source_id=source.id,
            external_code=code,
            name=f"Banco de Espana - {code}",
            description="Serie macroeconomica",
            frequency="monthly",
            source_url=f"{connector.base_url}/{code}",
            raw={"code": code},
        )
        for row in rows:
            fetched += 1
            try:
                dt = _parse_bde_date(row.get("date") or row.get("fecha"))
                if not dt:
                    continue
                value = row.get("value", row.get("valor"))
                insert_observation(
                    db,
                    series_id=serie.id,
                    obs_date=dt.date(),
                    obs_value=to_decimal(value),
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
