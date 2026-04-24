from __future__ import annotations

from datetime import UTC, datetime

from app.connectors.ine.connector import INEConnector
from app.db.session import SessionLocal
from app.services.ingest import (
    ensure_source,
    finish_run,
    insert_observation,
    start_run,
    upsert_series,
)
from app.utils.normalization import to_decimal


def _parse_ine_date(value: object | None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        # INE frequently returns epoch milliseconds in "Fecha".
        ts = float(value)
        if ts > 10_000_000_000:
            ts = ts / 1000.0
        return datetime.fromtimestamp(ts, tz=UTC).replace(tzinfo=None)
    if isinstance(value, str) and value.isdigit():
        return _parse_ine_date(int(value))
    for fmt in ("%Y-%m-%d", "%Y%m", "%Y"):
        try:
            dt = datetime.strptime(str(value), fmt)
            if fmt == "%Y%m":
                return datetime(dt.year, dt.month, 1)
            if fmt == "%Y":
                return datetime(dt.year, 1, 1)
            return dt
        except ValueError:
            continue
    return None


async def run(
    code: str | None = None,
    table: str | None = None,
    dry_run: bool = False,
) -> dict[str, object]:
    db = SessionLocal()
    connector = INEConnector()
    fetched = inserted = updated = failed = 0
    try:
        source = ensure_source(db, "ine", "Instituto Nacional de Estadistica", connector.base_url)
        source_run = start_run(db, source.id, "ingest_ine_series", dry_run)
        rows = await connector.fetch(code=code, table=table)
        for row in rows:
            fetched += 1
            try:
                code_val = str(row.get("COD", row.get("Id", f"INE-{fetched}")))
                name = row.get("Nombre") or row.get("NombreSerie") or f"Serie {code_val}"
                serie = upsert_series(
                    db,
                    source_id=source.id,
                    external_code=code_val,
                    name=name,
                    description=row.get("FK_TipoDato"),
                    unit=row.get("Unidad"),
                    frequency=row.get("Periodicidad"),
                    source_url=f"{connector.base_url}/DATOS_SERIE/{code_val}",
                    raw=row,
                )
                data = row.get("Data") or row.get("Valores") or []
                for point in data:
                    dt = _parse_ine_date(point.get("Fecha"))
                    if dt is None:
                        continue
                    insert_observation(
                        db,
                        series_id=serie.id,
                        obs_date=dt.date(),
                        obs_value=to_decimal(point.get("Valor")),
                        raw_payload=point,
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
