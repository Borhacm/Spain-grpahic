from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable

from app.editorial.tasks.jobs import (
    archive_low_score_candidates,
    detect_daily_signals,
    detect_weekly_signals,
    evaluate_rule_accuracy_alerts,
    generate_candidate_drafts,
    refresh_scores,
    suggest_crosses,
)
from app.pipelines.bootstrap_real_ine import run as bootstrap_real_ine
from app.pipelines.bootstrap_real_ine_public_story import run as bootstrap_real_ine_public_story
from app.pipelines.ingest_bde_series import run as ingest_bde_series
from app.pipelines.ingest_catalog_datosgob import run as ingest_catalog_datosgob
from app.pipelines.ingest_cnmv_issuers import run as ingest_cnmv_issuers
from app.pipelines.ingest_ine_series import run as ingest_ine_series
from app.pipelines.ingest_fmi_series import run as ingest_fmi_series
from app.pipelines.ingest_oecd_series import run as ingest_oecd_series
from app.pipelines.maintenance_dedupe_observations import run as maintenance_dedupe_observations
from app.pipelines.stubs import (
    backfill_story_summaries,
    ingest_aemet_observations,
    ingest_aemet_stations,
    ingest_bme_listed_companies,
    ingest_registradores_companies,
)

PipelineCallable = Callable[..., Awaitable[dict[str, object]]]


PIPELINES: dict[str, PipelineCallable] = {
    "ingest_datosgob_catalog": ingest_catalog_datosgob,
    "ingest_ine_series": ingest_ine_series,
    "ingest_bde_series": ingest_bde_series,
    "ingest_oecd_series": ingest_oecd_series,
    "ingest_fmi_series": ingest_fmi_series,
    "ingest_aemet_stations": ingest_aemet_stations,
    "ingest_aemet_observations": ingest_aemet_observations,
    "ingest_cnmv_issuers": ingest_cnmv_issuers,
    "ingest_registradores_companies": ingest_registradores_companies,
    "ingest_bme_listed_companies": ingest_bme_listed_companies,
    "bootstrap_real_ine": bootstrap_real_ine,
    "bootstrap_real_ine_public_story": bootstrap_real_ine_public_story,
    "maintenance_dedupe_observations": maintenance_dedupe_observations,
    "backfill_story_summaries": backfill_story_summaries,
    "detect_daily_signals": detect_daily_signals,
    "detect_weekly_signals": detect_weekly_signals,
    "refresh_scores": refresh_scores,
    "generate_candidate_drafts": generate_candidate_drafts,
    "suggest_crosses": suggest_crosses,
    "archive_low_score_candidates": archive_low_score_candidates,
    "evaluate_rule_accuracy_alerts": evaluate_rule_accuracy_alerts,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ingestion pipelines")
    parser.add_argument("pipeline", choices=PIPELINES.keys())
    parser.add_argument("--code", help="Series code for INE/BDE/OECD/FMI")
    parser.add_argument("--country", help="Country code for FMI (default ESP)")
    parser.add_argument("--table", help="Table code for INE")
    parser.add_argument("--keyword", help="Keyword for datos.gob")
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument(
        "--publish",
        action="store_true",
        default=False,
        help="Solo para bootstrap_real_ine_public_story: publicar en vivo (omitir borrador).",
    )
    return parser.parse_args()


async def _run_from_args(args: argparse.Namespace) -> dict[str, object]:
    fn = PIPELINES[args.pipeline]
    kwargs: dict[str, object] = {"dry_run": args.dry_run}
    if args.pipeline == "bootstrap_real_ine_public_story":
        kwargs["publish_live"] = bool(args.publish)
    if args.code:
        kwargs["code"] = args.code
    if args.country:
        kwargs["country"] = args.country
    if args.table:
        kwargs["table"] = args.table
    if args.keyword:
        kwargs["keyword"] = args.keyword
    return await fn(**kwargs)


def main() -> None:
    args = parse_args()
    result = asyncio.run(_run_from_args(args))
    print(result)


if __name__ == "__main__":
    main()
