"""Capa editorial: historias públicas (`public_stories`) desacopladas del candidato y del CMS."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.editorial.models import PublicStory, StoryCandidate
from app.editorial.repositories.candidates import review_action, set_candidate_status
from app.editorial.schemas.public_api import (
    ChartOptions,
    ChartSeriesDataset,
    ChartSpec,
    PublicCorrelationItem,
    PublishCandidatePayload,
    PublicStoryDetail,
    PublicStoryListItem,
    PublicStoryListResponse,
)
from app.editorial.services.public_story_narrative import compute_default_narrative_bundle, merge_narrative_bundle
from app.editorial.services.publication_service import _chart_spec_for_publication


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "story"


def _stable_slug(*, title: str, candidate_id: int, explicit: str | None) -> str:
    if explicit and explicit.strip():
        base = _slugify(explicit.strip())[:180]
    else:
        base = _slugify(title)[:180]
    suffix = f"-{candidate_id}"
    if base.endswith(suffix):
        return base
    return f"{base}{suffix}"


def _coerce_chart_spec(raw: ChartSpec | dict[str, Any] | None) -> dict[str, Any]:
    if raw is None:
        return ChartSpec(type="line", series=[]).model_dump(exclude_none=True)
    if isinstance(raw, ChartSpec):
        return raw.model_dump(exclude_none=True)
    return ChartSpec.model_validate(raw).model_dump(exclude_none=True)


def build_primary_chart_spec_from_candidate(db: Session, candidate: StoryCandidate) -> dict[str, Any]:
    raw = _chart_spec_for_publication(db, candidate, payload_chart=None) or {}
    ctype = str(raw.get("chart_type") or candidate.suggested_chart_type or "line").lower()
    points_raw = raw.get("preview_points") if isinstance(raw.get("preview_points"), list) else []
    mapped: list[dict[str, Any]] = []
    for p in points_raw:
        if not isinstance(p, dict):
            continue
        d, v = p.get("date"), p.get("value")
        if d is not None and v is not None:
            mapped.append({"x": str(d), "y": float(v) if isinstance(v, (int, float)) else v})
    label = raw.get("series_name")
    if not isinstance(label, str):
        label = "Serie"
    spec = ChartSpec(
        type=ctype,
        x_field="x",
        y_field="y",
        series=[ChartSeriesDataset(key="primary", label=label, points=mapped)],
        options=ChartOptions(title=candidate.title, legend=True),
    )
    data = spec.model_dump(exclude_none=True)
    rationale = candidate.effective_chart_rationale
    if rationale:
        data["chart_rationale"] = rationale
    if raw.get("series_id") is not None:
        data["series_id"] = raw.get("series_id")
    # Alias consumido por clientes que aún esperan `preview_points` con date/value (p. ej. parsers legacy).
    if mapped:
        data["preview_points"] = [
            {"date": str(p["x"]), "value": float(p["y"]) if isinstance(p["y"], (int, float)) else p["y"]}
            for p in mapped
        ]
    return data


def _list_summary(row: PublicStory) -> str | None:
    if row.summary and row.summary.strip():
        return row.summary.strip()
    body = (row.body_markdown or "").strip()
    if not body:
        return None
    return body[:240] + ("…" if len(body) > 240 else "")


def list_public_stories(
    db: Session,
    *,
    page: int,
    page_size: int,
    topic: str | None,
    tag: str | None,
) -> PublicStoryListResponse:
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    stmt = select(PublicStory).where(PublicStory.status == "published")
    count_stmt = select(func.count()).select_from(PublicStory).where(PublicStory.status == "published")
    if topic:
        t = topic.strip().lower()
        stmt = stmt.where(PublicStory.topic == t)
        count_stmt = count_stmt.where(PublicStory.topic == t)
    if tag:
        needle = tag.strip().lower()
        if db.bind and db.bind.dialect.name == "postgresql":
            from sqlalchemy import cast
            from sqlalchemy.dialects.postgresql import JSONB

            stmt = stmt.where(PublicStory.tags.is_not(None)).where(cast(PublicStory.tags, JSONB).contains([needle]))
            count_stmt = (
                count_stmt.where(PublicStory.tags.is_not(None)).where(cast(PublicStory.tags, JSONB).contains([needle]))
            )
        else:
            from sqlalchemy import cast as sql_cast
            from sqlalchemy import String

            like_pat = f'%"{needle}"%'
            stmt = stmt.where(PublicStory.tags.is_not(None)).where(sql_cast(PublicStory.tags, String).like(like_pat))
            count_stmt = (
                count_stmt.where(PublicStory.tags.is_not(None)).where(sql_cast(PublicStory.tags, String).like(like_pat))
            )
    total = int(db.scalar(count_stmt) or 0)
    stmt = stmt.order_by(PublicStory.published_at.desc().nullslast(), PublicStory.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = list(db.scalars(stmt).all())
    items: list[PublicStoryListItem] = []
    for row in rows:
        items.append(
            PublicStoryListItem(
                id=row.id,
                slug=row.slug,
                title=row.title,
                subtitle=row.subtitle,
                dek=row.dek,
                topic=row.topic,
                tags=row.tags,
                published_at=row.published_at,
                updated_at=row.updated_at,
                summary=_list_summary(row),
                preview_chart_type=row.chart_type,
            )
        )
    return PublicStoryListResponse(items=items, total=total, page=page, page_size=page_size)


def get_public_story_by_slug(db: Session, slug: str) -> PublicStoryDetail | None:
    row = db.scalar(select(PublicStory).where(PublicStory.slug == slug, PublicStory.status == "published"))
    if not row:
        return None
    return _to_detail(db, row)


def _to_detail(db: Session, row: PublicStory) -> PublicStoryDetail:
    candidate = db.get(StoryCandidate, row.candidate_id)
    spec = dict(row.primary_chart_spec or {})
    computed = compute_default_narrative_bundle(
        db,
        candidate=candidate,
        primary_chart_spec=spec,
        public_title=row.title,
        topic=row.topic,
        tags=row.tags,
    )
    merged = merge_narrative_bundle(row.narrative_context_json, computed)
    correlations: list[PublicCorrelationItem] = []
    for item in merged.get("correlations") or []:
        if not isinstance(item, dict):
            continue
        try:
            correlations.append(PublicCorrelationItem.model_validate(item))
        except Exception:
            continue
    return PublicStoryDetail(
        id=row.id,
        slug=row.slug,
        title=row.title,
        subtitle=row.subtitle,
        dek=row.dek,
        body_markdown=row.body_markdown,
        topic=row.topic,
        tags=row.tags,
        primary_chart_spec=spec,
        secondary_chart_spec=dict(row.secondary_chart_spec) if row.secondary_chart_spec else None,
        chart_type=row.chart_type,
        sources=row.sources,
        summary=_list_summary(row),
        chart_public_caption=str(merged.get("chart_public_caption") or ""),
        analysis_economic=str(merged.get("analysis_economic") or ""),
        analysis_social=str(merged.get("analysis_social") or ""),
        correlations=correlations,
        published_at=row.published_at,
        language=row.language,
        updated_at=row.updated_at,
    )


def publish_candidate(
    db: Session,
    candidate_id: int,
    payload: PublishCandidatePayload,
    *,
    actor: str | None = None,
) -> PublicStory:
    candidate = db.get(StoryCandidate, candidate_id)
    if not candidate:
        raise ValueError("Candidate not found")

    existing = db.scalar(select(PublicStory).where(PublicStory.candidate_id == candidate_id))

    if existing is None:
        if candidate.status != "accepted":
            raise ValueError("Candidate must be in status 'accepted' to create the first public story")
    else:
        if candidate.status in {"discarded", "archived", "new", "reviewing"}:
            raise ValueError("Candidate state does not allow updating the public story")

    now = datetime.now(UTC)
    sched_in = payload.scheduled_at
    if sched_in is not None and sched_in.tzinfo is None:
        sched_in = sched_in.replace(tzinfo=UTC)

    if payload.save_as_draft:
        pub_status = "draft"
        published_at = None
        scheduled_at = None
    elif sched_in is not None and sched_in > now:
        pub_status = "scheduled"
        published_at = None
        scheduled_at = sched_in
    else:
        pub_status = "published"
        published_at = now
        scheduled_at = None

    primary = _coerce_chart_spec(payload.primary_chart_spec) if payload.primary_chart_spec is not None else None
    if primary is None:
        primary = build_primary_chart_spec_from_candidate(db, candidate)
    secondary = (
        _coerce_chart_spec(payload.secondary_chart_spec) if payload.secondary_chart_spec is not None else None
    )

    chart_type = (payload.chart_type or candidate.suggested_chart_type or primary.get("type") or "line")[:50]

    if existing is not None:
        if payload.slug and payload.slug.strip():
            slug = _stable_slug(title=payload.title, candidate_id=candidate_id, explicit=payload.slug)
        else:
            slug = existing.slug
    else:
        slug = _stable_slug(title=payload.title, candidate_id=candidate_id, explicit=payload.slug)

    if existing is None or existing.slug != slug:
        exclude_id = existing.id if existing is not None else -1
        clash = db.scalar(select(PublicStory).where(PublicStory.slug == slug, PublicStory.id != exclude_id))
        if clash:
            raise ValueError("Slug already in use by another story")

    tags = [t.strip().lower() for t in (payload.tags or []) if t and str(t).strip()]
    tags = tags or None

    topic = payload.topic.strip().lower() if payload.topic and payload.topic.strip() else None

    if existing:
        row = existing
        row.slug = slug
        row.title = payload.title
        row.subtitle = payload.subtitle
        row.dek = payload.dek
        row.body_markdown = payload.body_markdown
        row.topic = topic
        row.tags = tags
        row.summary = payload.summary
        row.primary_chart_spec = primary
        row.secondary_chart_spec = secondary
        row.chart_type = chart_type
        row.sources = payload.sources
        if payload.narrative_context is not None:
            row.narrative_context_json = dict(payload.narrative_context) if payload.narrative_context else None
        row.language = payload.language or "es"
        row.status = pub_status
        row.published_at = published_at
        row.scheduled_at = scheduled_at
        row.published_by = actor
        row.updated_at = now
    else:
        row = PublicStory(
            slug=slug,
            title=payload.title,
            subtitle=payload.subtitle,
            dek=payload.dek,
            body_markdown=payload.body_markdown,
            topic=topic,
            tags=tags,
            summary=payload.summary,
            primary_chart_spec=primary,
            secondary_chart_spec=secondary,
            chart_type=chart_type,
            candidate_id=candidate_id,
            sources=payload.sources,
            narrative_context_json=dict(payload.narrative_context)
            if payload.narrative_context
            else None,
            status=pub_status,
            language=payload.language or "es",
            published_at=published_at,
            scheduled_at=scheduled_at,
            published_by=actor,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    db.flush()

    review_action(
        db,
        candidate_id,
        action="publish_public_story",
        reviewer=actor,
        notes=f"public_story_id={row.id} status={pub_status}",
        metadata_json={
            "public_story_id": row.id,
            "slug": row.slug,
            "status": pub_status,
            "published_at": published_at.isoformat() if published_at else None,
            "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
        },
    )

    if pub_status == "published":
        set_candidate_status(candidate, "published")

    db.flush()
    return row
