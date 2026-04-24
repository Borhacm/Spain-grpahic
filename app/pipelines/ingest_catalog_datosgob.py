from __future__ import annotations

from app.connectors.datosgob.connector import DatosGobConnector
from app.db.session import SessionLocal
from app.services.ingest import (
    ensure_source,
    finish_run,
    start_run,
    upsert_dataset,
    upsert_dataset_resource,
)


async def run(dry_run: bool = False, keyword: str | None = None) -> dict[str, int | str]:
    db = SessionLocal()
    connector = DatosGobConnector()
    fetched = inserted = updated = failed = 0
    try:
        source = ensure_source(db, "datosgob", "datos.gob.es", connector.base_url)
        source_run = start_run(db, source.id, "ingest_catalog_datosgob", dry_run)
        items = await connector.fetch(keyword=keyword)
        for item in items:
            fetched += 1
            try:
                dataset, is_new = upsert_dataset(
                    db,
                    source_id=source.id,
                    external_id=item.get("_id", item.get("identifier", f"dataset-{fetched}")),
                    title=item.get("title", "Untitled dataset"),
                    description=item.get("description"),
                    topic=(item.get("theme") or [None])[0] if isinstance(item.get("theme"), list) else item.get("theme"),
                    publisher=(item.get("publisher") or {}).get("label")
                    if isinstance(item.get("publisher"), dict)
                    else str(item.get("publisher", "")),
                    geography_scope=item.get("spatial"),
                    update_frequency=item.get("accrualPeriodicity"),
                    license=item.get("license"),
                    source_url=item.get("landingPage"),
                    raw=item,
                )
                for resource in item.get("distribution", []) or []:
                    upsert_dataset_resource(db, dataset.id, resource.get("_id"), resource)
                inserted += int(is_new)
                updated += int(not is_new)
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
