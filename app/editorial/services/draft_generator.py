from __future__ import annotations

from app.editorial.models import StoryCandidate


def generate_draft_payload(candidate: StoryCandidate) -> dict[str, object]:
    title = (candidate.title or "Indicador estadístico").strip()
    insight = (candidate.insight or "").strip()
    summary = (candidate.executive_summary or "").strip()
    why = (candidate.why_it_matters or "Ampliar contexto territorial o de política pública.").strip()

    lead = f"{title}. {insight}" if insight else title
    if summary and insight:
        base = f"{summary}\n\n{insight}"
    else:
        base = summary or insight or title

    analytical = f"Qué muestra: {insight or summary}\n\nPor qué importa: {why}"
    short = f"{title} — {insight}" if insight else title
    headlines = [
        title,
        f"{title}: lectura para la redacción",
        f"Contexto en España: {title}",
    ]
    questions = [
        "¿Qué factor estructural explica este cambio?",
        "¿Es un efecto puntual o una tendencia persistente?",
        "¿Qué territorios o sectores amplifican el fenómeno?",
    ]
    warnings = [
        "Borrador automático: debe revisarlo una persona antes de publicar.",
        "Verificar revisiones metodológicas de la fuente.",
        "Comprobar posible sesgo por estacionalidad.",
    ]
    return {
        "lead_neutral": lead,
        "base_paragraph": base,
        "analytical_version": analytical,
        "short_version": short,
        "alt_headlines_json": headlines,
        "followup_questions_json": questions,
        "warnings_json": warnings,
    }
