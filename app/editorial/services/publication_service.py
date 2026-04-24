from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
import re
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.editorial.models import CandidateRelatedSeries, PublicationTarget, PublishedStory, StoryCandidate
from app.editorial.repositories.candidates import set_candidate_status
from app.models import Series, SeriesObservation


class PublicationAdapter(ABC):
    @abstractmethod
    def publish(self, candidate: StoryCandidate, target: PublicationTarget) -> dict[str, Any]:
        raise NotImplementedError


class DryRunAdapter(PublicationAdapter):
    def publish(self, candidate: StoryCandidate, target: PublicationTarget) -> dict[str, Any]:
        return {
            "external_id": f"dryrun-{candidate.id}",
            "url": None,
            "status": "published",
            "payload": {"title": candidate.title, "target": target.slug, "mode": "dry_run"},
        }


class WebhookAdapter(PublicationAdapter):
    def publish(self, candidate: StoryCandidate, target: PublicationTarget) -> dict[str, Any]:
        config = dict(target.config_json or {})
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            raise ValueError("Missing webhook_url in publication target config")
        timeout = float(config.get("timeout_seconds", 10))
        payload = {
            "candidate_id": candidate.id,
            "title": candidate.title,
            "insight": candidate.insight,
            "executive_summary": candidate.executive_summary,
            "why_it_matters": candidate.why_it_matters,
        }
        with httpx.Client(timeout=timeout) as client:
            response = client.post(str(webhook_url), json=payload)
            response.raise_for_status()
            body = response.json() if response.content else {}
        return {
            "external_id": body.get("id") or f"webhook-{candidate.id}",
            "url": body.get("url"),
            "status": body.get("status", "published"),
            "payload": {"request": payload, "response": body, "target": target.slug},
        }


def get_adapter(adapter_type: str) -> PublicationAdapter:
    if adapter_type == "webhook":
        return WebhookAdapter()
    return DryRunAdapter()


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "story"


def _build_sources(payload: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    if not payload:
        return None
    payload_sources = payload.get("sources")
    if isinstance(payload_sources, list):
        normalized = [item for item in payload_sources if isinstance(item, dict)]
        if normalized:
            return normalized
    return None


def _chart_spec_for_publication(
    db: Session,
    candidate: StoryCandidate,
    *,
    payload_chart: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if isinstance(payload_chart, dict):
        base: dict[str, Any] = dict(payload_chart)
    else:
        base = dict(candidate.chart_spec_json or {})
    if candidate.suggested_chart_type:
        base.setdefault("chart_type", candidate.suggested_chart_type)
    rel = db.scalar(
        select(CandidateRelatedSeries)
        .where(CandidateRelatedSeries.candidate_id == candidate.id)
        .where(CandidateRelatedSeries.relation_type == "primary")
        .limit(1)
    )
    if rel is None:
        rel = db.scalar(
            select(CandidateRelatedSeries)
            .where(CandidateRelatedSeries.candidate_id == candidate.id)
            .order_by(CandidateRelatedSeries.id.asc())
            .limit(1)
        )
    if rel is not None:
        series = db.get(Series, rel.series_id)
        obs_rows = list(
            db.scalars(
                select(SeriesObservation)
                .where(SeriesObservation.series_id == rel.series_id)
                .order_by(SeriesObservation.obs_date.desc())
                .limit(72)
            ).all()
        )
        obs_rows.reverse()
        base["series_id"] = rel.series_id
        if series:
            base["series_name"] = series.name
        preview: list[dict[str, Any]] = []
        for o in obs_rows:
            if o.obs_value is None:
                continue
            val = o.obs_value
            preview.append(
                {
                    "date": o.obs_date.isoformat(),
                    "value": float(val),
                }
            )
        if preview:
            base["preview_points"] = preview
    return base or None


def send_to_publication_target(db: Session, candidate_id: int, target_slug: str) -> PublishedStory:
    candidate = db.get(StoryCandidate, candidate_id)
    if not candidate:
        raise ValueError("Candidate not found")
    target = db.query(PublicationTarget).filter(PublicationTarget.slug == target_slug).first()
    if not target:
        raise ValueError("Publication target not found")
    adapter = get_adapter(target.adapter_type)
    result = adapter.publish(candidate, target)
    payload = result.get("payload") if isinstance(result.get("payload"), dict) else {}
    raw_tags = payload.get("tags")
    tags = [str(item) for item in raw_tags] if isinstance(raw_tags, list) else []
    raw_topic = payload.get("topic")
    topic = str(raw_topic).strip().lower() if raw_topic else None
    published_at = datetime.now(UTC)
    slug_base = _slugify(str(payload.get("slug") or candidate.title))
    slug = f"{slug_base}-{candidate.id}"
    payload_chart = payload.get("chart_spec") if isinstance(payload.get("chart_spec"), dict) else None
    chart_spec = _chart_spec_for_publication(db, candidate, payload_chart=payload_chart)

    row = PublishedStory(
        candidate_id=candidate.id,
        target_id=target.id,
        slug=slug,
        title=str(payload.get("title") or candidate.title),
        subtitle=str(payload.get("subtitle") or candidate.executive_summary or "") or None,
        body=str(payload.get("body") or candidate.insight),
        chart_spec=chart_spec,
        topic=topic,
        tags=tags or None,
        sources=_build_sources(payload),
        external_id=result.get("external_id"),
        url=result.get("url"),
        status=result.get("status", "queued"),
        payload_json=payload,
        published_at=published_at,
        updated_at=published_at,
    )
    db.add(row)
    set_candidate_status(candidate, "published")
    db.flush()
    return row
