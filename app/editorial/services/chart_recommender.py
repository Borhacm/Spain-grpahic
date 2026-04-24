from __future__ import annotations

from collections.abc import Iterable

from app.editorial.models import StoryCandidate

HOUSING_KEYWORDS = {
    "vivienda",
    "alquiler",
    "hipoteca",
    "precio de la vivienda",
    "esfuerzo de acceso",
    "mercado inmobiliario",
}
HOUSING_SOURCE_SLUGS = {"idealista", "fotocasa", "mitma", "ine"}
ECONOMY_KEYWORDS = {
    "economia",
    "macro",
    "inflacion",
    "ipc",
    "pib",
    "paro",
    "desempleo",
    "salario",
    "ahorro",
    "deuda",
    "tipos de interes",
    "banco de espana",
    "ine",
    "euribor",
}
ECONOMY_SOURCE_SLUGS = {"ine", "bde", "banco-de-espana", "aemet", "cnmv", "datosgob"}
CLIMATE_KEYWORDS = {
    "clima",
    "temperatura",
    "precipitacion",
    "lluvia",
    "sequia",
    "ola de calor",
    "ola de frio",
    "record termico",
    "anomalia termica",
}
CLIMATE_SOURCE_SLUGS = {"aemet"}
COMPANY_KEYWORDS = {
    "empresa",
    "cotizada",
    "acciones",
    "mercado",
    "beneficio",
    "margen",
    "deuda",
    "ratio",
    "ebitda",
    "valoracion",
    "sector",
    "bursa",
}
COMPANY_SOURCE_SLUGS = {"cnmv", "bme", "registradores"}
TREND_KEYWORDS = {
    "tendencia",
    "evolucion",
    "interanual",
    "mensual",
    "historico",
    "ultimo periodo",
    "serie temporal",
}
COMPARISON_CATEGORY_KEYWORDS = {
    "ccaa",
    "comunidad",
    "provincias",
    "sectores",
    "sectorial",
    "tramo de edad",
    "ranking",
    "comparativa",
}
RELATIVE_EVOLUTION_KEYWORDS = {
    "divergencia",
    "convergencia",
    "trayectoria",
    "evolucion relativa",
    "comparacion relativa",
}
RELATION_KEYWORDS = {
    "relacion",
    "correlacion",
    "vs",
    "frente a",
    "impacta en",
    "impacto sobre",
}
DISTRIBUTION_KEYWORDS = {"distribucion", "percentil", "dispersion", "cuartil"}
SPATIAL_KEYWORDS = {"mapa", "regional", "provincia", "municipio", "territorial"}
PRECIPITATION_KEYWORDS = {"precipitacion", "lluvia", "pluviometria"}
TEMPERATURE_KEYWORDS = {"temperatura", "termica", "calor", "frio"}
EXTREME_CLIMATE_KEYWORDS = {"record", "extremo", "ola de calor", "ola de frio", "maximo", "minimo"}
RANKING_KEYWORDS = {"ranking", "top", "bottom", "mejores", "peores", "lideres"}


def _normalize_tokens(values: Iterable[str | None]) -> str:
    return " ".join(value.lower() for value in values if value).strip()


def is_economy_candidate(
    candidate: StoryCandidate,
    *,
    source_slugs: Iterable[str] | None = None,
    category_names: Iterable[str] | None = None,
) -> bool:
    text_blob = _normalize_tokens(
        [
            candidate.title,
            candidate.insight,
            candidate.executive_summary,
            candidate.why_it_matters,
            candidate.geography,
            candidate.period_label,
        ]
    )
    if any(keyword in text_blob for keyword in ECONOMY_KEYWORDS):
        return True

    source_tokens = {item.lower() for item in (source_slugs or []) if item}
    if source_tokens.intersection(ECONOMY_SOURCE_SLUGS):
        return True

    category_blob = _normalize_tokens(category_names or [])
    return any(keyword in category_blob for keyword in ECONOMY_KEYWORDS)


def is_housing_candidate(
    candidate: StoryCandidate,
    *,
    source_slugs: Iterable[str] | None = None,
    category_names: Iterable[str] | None = None,
) -> bool:
    text_blob = _normalize_tokens(
        [candidate.title, candidate.insight, candidate.executive_summary, candidate.why_it_matters]
    )
    if any(keyword in text_blob for keyword in HOUSING_KEYWORDS):
        return True
    source_tokens = {item.lower() for item in (source_slugs or []) if item}
    if source_tokens.intersection(HOUSING_SOURCE_SLUGS):
        return True
    category_blob = _normalize_tokens(category_names or [])
    return any(keyword in category_blob for keyword in HOUSING_KEYWORDS)


def is_climate_candidate(
    candidate: StoryCandidate,
    *,
    source_slugs: Iterable[str] | None = None,
    category_names: Iterable[str] | None = None,
) -> bool:
    text_blob = _normalize_tokens(
        [candidate.title, candidate.insight, candidate.executive_summary, candidate.why_it_matters]
    )
    if any(keyword in text_blob for keyword in CLIMATE_KEYWORDS):
        return True
    source_tokens = {item.lower() for item in (source_slugs or []) if item}
    if source_tokens.intersection(CLIMATE_SOURCE_SLUGS):
        return True
    category_blob = _normalize_tokens(category_names or [])
    return any(keyword in category_blob for keyword in CLIMATE_KEYWORDS)


def is_company_candidate(
    candidate: StoryCandidate,
    *,
    source_slugs: Iterable[str] | None = None,
    category_names: Iterable[str] | None = None,
    signal_types: Iterable[str] | None = None,
) -> bool:
    text_blob = _normalize_tokens(
        [candidate.title, candidate.insight, candidate.executive_summary, candidate.why_it_matters]
    )
    if any(keyword in text_blob for keyword in COMPANY_KEYWORDS):
        return True
    source_tokens = {item.lower() for item in (source_slugs or []) if item}
    if source_tokens.intersection(COMPANY_SOURCE_SLUGS):
        return True
    signal_set = {item.lower() for item in (signal_types or []) if item}
    if {"new_filing", "business_fabric_change"}.intersection(signal_set):
        return True
    category_blob = _normalize_tokens(category_names or [])
    return any(keyword in category_blob for keyword in COMPANY_KEYWORDS)


def suggest_chart_type_for_housing(
    candidate: StoryCandidate,
    *,
    source_slugs: Iterable[str] | None = None,
    category_names: Iterable[str] | None = None,
    signal_types: Iterable[str] | None = None,
    series_count: int = 1,
) -> tuple[str | None, str | None]:
    if not is_housing_candidate(candidate, source_slugs=source_slugs, category_names=category_names):
        return None, None
    text_blob = _normalize_tokens([candidate.title, candidate.insight, candidate.executive_summary])
    signal_set = {item.lower() for item in (signal_types or []) if item}

    if any(keyword in text_blob for keyword in RELATION_KEYWORDS):
        return "scatter", "Relacion entre metricas de vivienda (precio, esfuerzo, renta)."
    if any(keyword in text_blob for keyword in COMPARISON_CATEGORY_KEYWORDS):
        if series_count > 1:
            return "multi_line", "Comparativa de evolucion entre territorios o segmentos de vivienda."
        return "bar", "Comparacion por categoria/territorio en un periodo."
    if "series_divergence" in signal_set:
        return "multi_line", "Divergencia entre series de vivienda."
    return "line", "Serie temporal de mercado inmobiliario."


def suggest_chart_type_for_economy(
    candidate: StoryCandidate,
    *,
    source_slugs: Iterable[str] | None = None,
    category_names: Iterable[str] | None = None,
    signal_types: Iterable[str] | None = None,
    series_count: int = 1,
) -> tuple[str | None, str | None]:
    if not is_economy_candidate(
        candidate,
        source_slugs=source_slugs,
        category_names=category_names,
    ):
        return None, None

    signal_set = {item.lower() for item in (signal_types or []) if item}
    text_blob = _normalize_tokens(
        [
            candidate.title,
            candidate.insight,
            candidate.executive_summary,
            candidate.why_it_matters,
        ]
    )

    if "series_divergence" in signal_set or any(keyword in text_blob for keyword in RELATIVE_EVOLUTION_KEYWORDS):
        return "multi_line", "Comparacion relativa de evolucion entre series comparables."

    if any(keyword in text_blob for keyword in RELATION_KEYWORDS):
        return "scatter", "Relacion entre dos indicadores macroeconomicos."

    if any(keyword in text_blob for keyword in COMPARISON_CATEGORY_KEYWORDS):
        if series_count > 1:
            return "multi_line", "Comparativa de evolucion entre categorias/territorios."
        return "bar", "Comparacion de magnitudes entre categorias en un mismo corte."

    if any(keyword in text_blob for keyword in DISTRIBUTION_KEYWORDS):
        return "histogram", "Analisis de distribucion de valores en la muestra."

    if any(keyword in text_blob for keyword in TREND_KEYWORDS) or signal_set:
        return "line", "Seguimiento de tendencia temporal de indicador economico."

    return "line", "Indicador macro de serie temporal, visualizado como tendencia."


def suggest_chart_type_for_climate(
    candidate: StoryCandidate,
    *,
    source_slugs: Iterable[str] | None = None,
    category_names: Iterable[str] | None = None,
    signal_types: Iterable[str] | None = None,
    series_names: Iterable[str] | None = None,
    series_count: int = 1,
    has_spatial_data: bool = False,
) -> tuple[str | None, str | None]:
    if not is_climate_candidate(candidate, source_slugs=source_slugs, category_names=category_names):
        return None, None
    text_blob = _normalize_tokens(
        [
            candidate.title,
            candidate.insight,
            candidate.executive_summary,
            candidate.why_it_matters,
            _normalize_tokens(series_names or []),
        ]
    )
    signal_set = {item.lower() for item in (signal_types or []) if item}

    if has_spatial_data and any(keyword in text_blob for keyword in SPATIAL_KEYWORDS):
        return "map", "Comparativa espacial del fenomeno climatico entre regiones."
    if any(keyword in text_blob for keyword in EXTREME_CLIMATE_KEYWORDS) or {
        "historical_max",
        "historical_min",
        "statistical_anomaly",
    }.intersection(signal_set):
        return "line_with_annotations", "Serie temporal con foco en extremos y records climaticos."
    if any(keyword in text_blob for keyword in PRECIPITATION_KEYWORDS):
        return "column", "Precipitacion agregada por periodo para comparar volumenes."
    if any(keyword in text_blob for keyword in COMPARISON_CATEGORY_KEYWORDS) and series_count <= 1:
        return "bar", "Comparacion climatica entre regiones/categorias en un corte temporal."
    if any(keyword in text_blob for keyword in TEMPERATURE_KEYWORDS) or signal_set:
        return "line", "Evolucion temporal de variable climatica."
    return "line", "Serie temporal climatica para seguimiento de tendencia."


def suggest_chart_type_for_companies(
    candidate: StoryCandidate,
    *,
    source_slugs: Iterable[str] | None = None,
    category_names: Iterable[str] | None = None,
    signal_types: Iterable[str] | None = None,
    series_count: int = 1,
) -> tuple[str | None, str | None]:
    if not is_company_candidate(
        candidate,
        source_slugs=source_slugs,
        category_names=category_names,
        signal_types=signal_types,
    ):
        return None, None
    text_blob = _normalize_tokens(
        [candidate.title, candidate.insight, candidate.executive_summary, candidate.why_it_matters]
    )
    signal_set = {item.lower() for item in (signal_types or []) if item}

    if any(keyword in text_blob for keyword in RELATION_KEYWORDS):
        return "scatter", "Relacion entre dos metricas financieras/empresariales."
    if any(keyword in text_blob for keyword in RANKING_KEYWORDS):
        return "bar", "Ranking de empresas por metrica en un periodo."
    if any(keyword in text_blob for keyword in COMPARISON_CATEGORY_KEYWORDS):
        return "heatmap", "Comparacion sectorial agregada en matriz sector-metrica."
    if "series_divergence" in signal_set and series_count > 1:
        return "multi_line", "Comparacion de evolucion relativa entre cotizadas/sectores."
    return "line", "Evolucion temporal de precio o metrica financiera."


def suggest_chart_type(
    candidate: StoryCandidate,
    *,
    source_slugs: Iterable[str] | None = None,
    category_names: Iterable[str] | None = None,
    signal_types: Iterable[str] | None = None,
    series_names: Iterable[str] | None = None,
    series_count: int = 1,
    has_spatial_data: bool = False,
) -> tuple[str, str]:
    for recommender in (
        lambda: suggest_chart_type_for_housing(
            candidate,
            source_slugs=source_slugs,
            category_names=category_names,
            signal_types=signal_types,
            series_count=series_count,
        ),
        lambda: suggest_chart_type_for_climate(
            candidate,
            source_slugs=source_slugs,
            category_names=category_names,
            signal_types=signal_types,
            series_names=series_names,
            series_count=series_count,
            has_spatial_data=has_spatial_data,
        ),
        lambda: suggest_chart_type_for_companies(
            candidate,
            source_slugs=source_slugs,
            category_names=category_names,
            signal_types=signal_types,
            series_count=series_count,
        ),
        lambda: suggest_chart_type_for_economy(
            candidate,
            source_slugs=source_slugs,
            category_names=category_names,
            signal_types=signal_types,
            series_count=series_count,
        ),
    ):
        chart_type, rationale = recommender()
        if chart_type:
            return chart_type, rationale or "Regla de visualizacion tematica aplicada."

    text_blob = _normalize_tokens([candidate.title, candidate.insight, candidate.executive_summary])
    if any(keyword in text_blob for keyword in COMPARISON_CATEGORY_KEYWORDS):
        return "bar", "Fallback generico para comparacion categorica."
    return "line", "Fallback generico para serie temporal."
