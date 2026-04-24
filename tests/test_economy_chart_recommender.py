from app.editorial.models import StoryCandidate
from app.editorial.services.chart_recommender import suggest_chart_type_for_economy


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


def test_economy_time_series_candidate_suggests_line() -> None:
    candidate = _candidate(
        "Inflacion en Espana acelera en enero",
        "La tendencia interanual del IPC sigue al alza en los ultimos meses.",
    )
    chart_type, _ = suggest_chart_type_for_economy(
        candidate,
        source_slugs=["ine"],
        category_names=["Precios"],
        signal_types=["yoy_change"],
        series_count=1,
    )
    assert chart_type == "line"


def test_economy_category_comparison_suggests_bar() -> None:
    candidate = _candidate(
        "Comparativa del paro por CCAA",
        "Comparativa por comunidades autonomas en el ultimo trimestre.",
    )
    chart_type, _ = suggest_chart_type_for_economy(
        candidate,
        source_slugs=["ine"],
        category_names=["Mercado laboral"],
        signal_types=[],
        series_count=1,
    )
    assert chart_type == "bar"


def test_economy_multiseries_comparison_suggests_multi_line() -> None:
    candidate = _candidate(
        "Divergencia salarial entre sectores",
        "La evolucion relativa entre sectores muestra trayectorias opuestas.",
    )
    chart_type, _ = suggest_chart_type_for_economy(
        candidate,
        source_slugs=["ine"],
        category_names=["Salarios"],
        signal_types=["series_divergence"],
        series_count=2,
    )
    assert chart_type == "multi_line"


def test_economy_relationship_between_indicators_suggests_scatter() -> None:
    candidate = _candidate(
        "Inflacion vs tipos de interes",
        "Analisis de relacion entre inflacion y tipos de interes.",
    )
    chart_type, _ = suggest_chart_type_for_economy(
        candidate,
        source_slugs=["bde"],
        category_names=["Macro"],
        signal_types=[],
        series_count=2,
    )
    assert chart_type == "scatter"
