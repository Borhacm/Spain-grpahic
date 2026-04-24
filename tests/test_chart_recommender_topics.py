from app.editorial.models import StoryCandidate
from app.editorial.services.chart_recommender import (
    suggest_chart_type,
    suggest_chart_type_for_climate,
    suggest_chart_type_for_companies,
)


def _candidate(title: str, insight: str) -> StoryCandidate:
    return StoryCandidate(
        dedupe_hash=f"hash::{title}",
        title=title,
        insight=insight,
        executive_summary=None,
        why_it_matters=None,
        geography="ES",
        period_label="2025-01",
        status="new",
    )


def test_climate_temperature_series_suggests_line() -> None:
    candidate = _candidate(
        "Temperatura media mensual en Espana",
        "Evolucion de la temperatura mensual durante el ultimo ano.",
    )
    chart_type, _ = suggest_chart_type_for_climate(
        candidate,
        source_slugs=["aemet"],
        category_names=["clima"],
        signal_types=["trend_break"],
        series_count=1,
    )
    assert chart_type == "line"


def test_climate_precipitation_suggests_column() -> None:
    candidate = _candidate(
        "Precipitacion acumulada trimestral",
        "Comparativa de lluvia acumulada por trimestre.",
    )
    chart_type, _ = suggest_chart_type_for_climate(
        candidate,
        source_slugs=["aemet"],
        category_names=["precipitacion"],
        signal_types=[],
        series_count=1,
    )
    assert chart_type == "column"


def test_climate_regional_comparison_suggests_bar() -> None:
    candidate = _candidate(
        "Comparativa de temperatura por CCAA",
        "Comparativa regional de temperaturas medias en el mismo periodo.",
    )
    chart_type, _ = suggest_chart_type_for_climate(
        candidate,
        source_slugs=["aemet"],
        category_names=["clima"],
        signal_types=[],
        series_count=1,
    )
    assert chart_type == "bar"


def test_company_price_timeseries_suggests_line() -> None:
    candidate = _candidate(
        "Evolucion del precio de una cotizada",
        "Serie temporal del precio de cierre de la empresa.",
    )
    chart_type, _ = suggest_chart_type_for_companies(
        candidate,
        source_slugs=["bme"],
        category_names=["cotizadas"],
        signal_types=[],
        series_count=1,
    )
    assert chart_type == "line"


def test_company_ranking_suggests_bar() -> None:
    candidate = _candidate(
        "Top de empresas por margen",
        "Ranking sectorial de las empresas con mayor margen operativo.",
    )
    chart_type, _ = suggest_chart_type_for_companies(
        candidate,
        source_slugs=["cnmv"],
        category_names=["empresas"],
        signal_types=[],
        series_count=1,
    )
    assert chart_type == "bar"


def test_company_metrics_relationship_suggests_scatter() -> None:
    candidate = _candidate(
        "Margen vs deuda en cotizadas",
        "Analisis de relacion entre margen y deuda financiera.",
    )
    chart_type, _ = suggest_chart_type_for_companies(
        candidate,
        source_slugs=["cnmv"],
        category_names=["empresas"],
        signal_types=[],
        series_count=2,
    )
    assert chart_type == "scatter"


def test_global_suggester_prioritizes_climate_over_economy() -> None:
    candidate = _candidate(
        "Inflacion y temperatura extrema en verano",
        "Record termico con impacto en consumo.",
    )
    chart_type, rationale = suggest_chart_type(
        candidate,
        source_slugs=["aemet"],
        category_names=["clima"],
        signal_types=["historical_max"],
        series_count=1,
        has_spatial_data=False,
    )
    assert chart_type == "line_with_annotations"
    assert "extremos" in (rationale or "").lower() or "records" in (rationale or "").lower()


def test_global_suggester_uses_generic_fallback() -> None:
    candidate = _candidate(
        "Indicador neutral sin tema claro",
        "Evolucion simple de una metrica operativa.",
    )
    chart_type, rationale = suggest_chart_type(
        candidate,
        source_slugs=["unknown"],
        category_names=["general"],
        signal_types=[],
        series_count=1,
    )
    assert chart_type == "line"
    assert "fallback" in rationale.lower()
