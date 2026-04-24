from __future__ import annotations

from app.editorial.models import StoryCandidate


DEFAULT_CROSSES: list[dict[str, str]] = [
    {
        "left_entity": "salario",
        "right_entity": "alquiler",
        "rationale": "Mide presion de coste de vida sobre renta disponible.",
        "suggested_angle": "Como evoluciona el esfuerzo de acceso a vivienda.",
        "suggested_chart_type": "line_dual_axis",
    },
    {
        "left_entity": "inflacion",
        "right_entity": "ahorro",
        "rationale": "Evalua perdida de poder adquisitivo y reaccion de hogares.",
        "suggested_angle": "Si sube precios, cae capacidad de ahorro.",
        "suggested_chart_type": "line_compare",
    },
    {
        "left_entity": "temperatura",
        "right_entity": "precipitacion",
        "rationale": "Explica patrones climaticos extremos.",
        "suggested_angle": "Contrastes de calor y lluvia por temporadas.",
        "suggested_chart_type": "scatter",
    },
]


def suggest_crosses(candidate: StoryCandidate) -> list[dict[str, str]]:
    topic = (candidate.title + " " + (candidate.insight or "")).lower()
    if "turismo" in topic:
        return [
            {
                "left_entity": "turismo",
                "right_entity": "precios",
                "rationale": "Relacion entre afluencia y tension de precios.",
                "suggested_angle": "Si el turismo empuja IPC local.",
                "suggested_chart_type": "line_compare",
            }
        ]
    if "empresa" in topic or "cotiz" in topic:
        return [
            {
                "left_entity": "cotizada",
                "right_entity": "sector",
                "rationale": "Compara rendimiento individual con media sectorial.",
                "suggested_angle": "Desempeño relativo frente a pares.",
                "suggested_chart_type": "bar_rank",
            }
        ]
    return DEFAULT_CROSSES
