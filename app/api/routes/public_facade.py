"""API pública versionada para la fachada web (historias publicadas en `public_stories`)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.editorial.schemas.public_api import (
    PublicCountryOverviewMappingStatusResponse,
    PublicCountryOverviewResponse,
    PublicStoryDetail,
    PublicStoryListResponse,
)
from app.editorial.services.country_overview_service import (
    get_country_overview_mapping_status,
    get_oecd_ranking_for_indicator,
    get_public_country_overview,
)
from app.editorial.services.public_story_service import get_public_story_by_slug, list_public_stories

router = APIRouter(prefix="/public", tags=["public-facade"])


@router.get(
    "/stories",
    response_model=PublicStoryListResponse,
    summary="Listar historias publicadas",
    description="Solo `status=published`. Paginación y filtros opcionales por `topic` y `tag`.",
)
def get_public_stories(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    topic: str | None = Query(default=None, description="Tema exacto (p. ej. economy, housing)"),
    tag: str | None = Query(default=None, description="Etiqueta presente en la lista `tags`"),
) -> PublicStoryListResponse:
    return list_public_stories(db, page=page, page_size=page_size, topic=topic, tag=tag)


@router.get(
    "/stories/by-topic/{topic}",
    response_model=PublicStoryListResponse,
    summary="Historias por tema (atajo)",
    description="Equivalente a `GET /public/stories?topic=` con paginación por defecto.",
)
def get_public_stories_by_topic_path(
    topic: str,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PublicStoryListResponse:
    return list_public_stories(db, page=page, page_size=page_size, topic=topic, tag=None)


@router.get(
    "/stories/{slug}",
    response_model=PublicStoryDetail,
    summary="Detalle de historia por slug",
    description="No expone `candidate_id` ni metadatos internos del middleware editorial.",
)
def get_public_story(slug: str, db: Session = Depends(get_db)) -> PublicStoryDetail:
    row = get_public_story_by_slug(db, slug)
    if not row:
        raise HTTPException(status_code=404, detail="Story not found")
    return row


@router.get(
    "/country-overview",
    response_model=PublicCountryOverviewResponse,
    summary="Ficha país España (dashboard)",
    description="Payload agregado para dashboard ejecutivo: KPIs, narrativa y secciones temáticas.",
)
def get_country_overview(
    db: Session = Depends(get_db),
    strict: bool = Query(
        default=False,
        description="Si es true, devuelve 422 cuando hay mappings sin resolver o con datos desactualizados.",
    ),
) -> PublicCountryOverviewResponse:
    if strict:
        mapping_status = get_country_overview_mapping_status(db)
        failures = [
            item
            for item in mapping_status.get("items", [])
            if (not item.get("mapped")) or item.get("is_stale")
        ]
        if failures:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "country_overview_mapping_incomplete",
                    "message": "COUNTRY_OVERVIEW_SERIES_MAP contiene mappings no resueltos o desactualizados.",
                    "failures": failures,
                },
            )
    payload = get_public_country_overview(db)
    return PublicCountryOverviewResponse.model_validate(payload)


@router.get(
    "/country-overview/mapping-status",
    response_model=PublicCountryOverviewMappingStatusResponse,
    summary="Estado del mapeo de series para ficha país",
    description="Diagnóstico de mappings COUNTRY_OVERVIEW_SERIES_MAP contra series/observaciones en la base de datos.",
)
def get_country_overview_mapping(db: Session = Depends(get_db)) -> PublicCountryOverviewMappingStatusResponse:
    payload = get_country_overview_mapping_status(db)
    return PublicCountryOverviewMappingStatusResponse.model_validate(payload)


@router.get(
    "/country-overview/ranking/{indicator_id}",
    summary="Ranking OECD para indicador comparativo",
    description="Devuelve ranking internacional del indicador OECD solicitado para España.",
)
def get_country_overview_oecd_ranking(
    indicator_id: str,
    country: str = Query(default="ESP", min_length=3, max_length=3),
) -> dict[str, object]:
    payload = get_oecd_ranking_for_indicator(indicator_id=indicator_id, country_code=country)
    if not payload:
        raise HTTPException(status_code=404, detail="Ranking not available for this indicator")
    return payload
