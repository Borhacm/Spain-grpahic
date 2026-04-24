"""Carga datos INE reales y materializa una historia en `public_stories` (middleware editorial → fachada)."""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.editorial.models import CandidateDraft, StoryCandidate
from app.editorial.schemas.public_api import PublishCandidatePayload
from app.editorial.services.public_story_service import publish_candidate
from app.editorial.services.review_service import set_candidate_state
from app.pipelines.bootstrap_real_ine import run as bootstrap_real_ine


def _body_from_candidate(candidate: StoryCandidate, draft: CandidateDraft | None) -> str:
    parts: list[str] = []
    if draft:
        if draft.lead_neutral and draft.lead_neutral.strip():
            parts.append(draft.lead_neutral.strip())
        if draft.base_paragraph and draft.base_paragraph.strip():
            parts.append(draft.base_paragraph.strip())
    if parts:
        return "\n\n".join(parts)
    insight = (candidate.insight or "").strip()
    if insight:
        return f"**Contexto**\n\n{insight}"
    return "Borrador generado automáticamente a partir del candidato editorial."


async def run(*, dry_run: bool = False, publish_live: bool = False) -> dict[str, object]:
    """Orquesta `bootstrap_real_ine` y crea/actualiza `public_stories` para el último candidato."""
    bootstrap_result = await bootstrap_real_ine(dry_run=dry_run)
    if dry_run:
        return {"dry_run": True, "bootstrap": bootstrap_result}

    db = SessionLocal()
    try:
        candidate = db.scalar(select(StoryCandidate).order_by(StoryCandidate.id.desc()).limit(1))
        if candidate is None:
            return {"bootstrap": bootstrap_result, "error": "no_story_candidates"}

        set_candidate_state(
            db,
            candidate.id,
            "accepted",
            reviewer="bootstrap_real_ine_public_story",
            notes="Aceptado automáticamente para materializar public_stories",
        )

        draft = db.scalar(select(CandidateDraft).where(CandidateDraft.candidate_id == candidate.id))
        body_markdown = _body_from_candidate(candidate, draft)
        subtitle = None
        if candidate.executive_summary and str(candidate.executive_summary).strip():
            subtitle = str(candidate.executive_summary).strip()[:2000]

        payload = PublishCandidatePayload(
            title=(candidate.title or "Historia editorial")[:500],
            subtitle=subtitle,
            dek=None,
            body_markdown=body_markdown,
            topic="economy",
            tags=["ine", "datos-reales"],
            summary=None,
            sources=[{"title": "Instituto Nacional de Estadística (INE)", "url": "https://www.ine.es"}],
            language="es",
            save_as_draft=not publish_live,
        )
        row = publish_candidate(db, candidate.id, payload, actor="bootstrap_real_ine_public_story")
        db.commit()
        return {
            "bootstrap": bootstrap_result,
            "candidate_id": candidate.id,
            "public_story_id": row.id,
            "slug": row.slug,
            "status": row.status,
            "publish_live": publish_live,
        }
    finally:
        db.close()
