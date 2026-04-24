from __future__ import annotations


async def ingest_aemet_stations(dry_run: bool = False) -> dict[str, object]:
    return {
        "status": "not_implemented",
        "pipeline": "ingest_aemet_stations",
        "dry_run": dry_run,
        "note": "AEMET adapter scaffolded; endpoint mapping pending.",
    }


async def ingest_aemet_observations(dry_run: bool = False) -> dict[str, object]:
    return {
        "status": "not_implemented",
        "pipeline": "ingest_aemet_observations",
        "dry_run": dry_run,
    }


async def ingest_cnmv_issuers(dry_run: bool = False) -> dict[str, object]:
    return {"status": "not_implemented", "pipeline": "ingest_cnmv_issuers", "dry_run": dry_run}


async def ingest_registradores_companies(dry_run: bool = False) -> dict[str, object]:
    return {
        "status": "not_implemented",
        "pipeline": "ingest_registradores_companies",
        "dry_run": dry_run,
    }


async def ingest_bme_listed_companies(dry_run: bool = False) -> dict[str, object]:
    return {
        "status": "not_implemented",
        "pipeline": "ingest_bme_listed_companies",
        "dry_run": dry_run,
    }


async def backfill_story_summaries(dry_run: bool = False) -> dict[str, object]:
    return {
        "status": "success",
        "pipeline": "backfill_story_summaries",
        "dry_run": dry_run,
        "processed": 0,
    }
