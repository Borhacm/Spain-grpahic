from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import get_db
from app.main import app
from app.models import Series, SeriesObservation, Source
from app.editorial.models import CandidateRelatedSeries, PublicStory, StoryCandidate
from app.editorial.schemas.public_api import ChartSeriesDataset, ChartSpec


def test_publish_candidate_creates_public_story(db_session) -> None:
    source = Source(slug="ps-source", name="PS Source", source_type="api", base_url="https://example.com")
    db_session.add(source)
    db_session.flush()
    series = Series(source_id=source.id, external_code="PS-1", name="Serie PS", frequency="monthly")
    db_session.add(series)
    db_session.flush()
    for idx, value in enumerate([Decimal("10"), Decimal("11"), Decimal("12")]):
        db_session.add(
            SeriesObservation(series_id=series.id, obs_date=date(2025, idx + 1, 1), obs_value=value)
        )
    cand = StoryCandidate(
        title="Historia PS",
        insight="Cuerpo insight",
        status="accepted",
        dedupe_hash="ps-test-1",
        suggested_chart_type="line",
    )
    db_session.add(cand)
    db_session.flush()
    from app.editorial.repositories.candidates import set_related_series

    set_related_series(db_session, cand.id, series.id)
    db_session.commit()

    def _db():
        yield db_session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app)

    payload = {
        "title": "Título público",
        "subtitle": "Sub",
        "dek": "Dek",
        "body_markdown": "## Hola\n\nTexto.",
        "topic": "economy",
        "tags": ["macro", "ipc"],
        "summary": "Resumen corto",
        "primary_chart_spec": ChartSpec(
            type="line",
            series=[ChartSeriesDataset(key="a", label="L", points=[{"x": "2025-01-01", "y": 1.0}])],
        ).model_dump(),
        "chart_type": "line",
        "sources": [{"title": "INE", "url": "https://www.ine.es"}],
    }
    resp = client.post(f"/candidates/{cand.id}/publish", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "published"
    assert data["slug"]

    row = db_session.get(PublicStory, data["public_story_id"])
    assert row is not None
    assert row.candidate_id == cand.id
    assert row.body_markdown.startswith("##")
    assert row.primary_chart_spec["type"] == "line"

    app.dependency_overrides.clear()


def test_editorial_ui_publish_web_creates_public_story(db_session) -> None:
    source = Source(slug="ui-ps-source", name="UI Source", source_type="api", base_url="https://example.com")
    db_session.add(source)
    db_session.flush()
    series = Series(source_id=source.id, external_code="UI-1", name="Serie UI", frequency="monthly")
    db_session.add(series)
    db_session.flush()
    for idx, value in enumerate([Decimal("1"), Decimal("2"), Decimal("3")]):
        db_session.add(
            SeriesObservation(series_id=series.id, obs_date=date(2025, idx + 1, 1), obs_value=value)
        )
    cand = StoryCandidate(
        title="Candidato UI",
        insight="Insight UI",
        status="accepted",
        dedupe_hash="ui-ps-web-1",
        suggested_chart_type="line",
    )
    db_session.add(cand)
    db_session.flush()
    from app.editorial.repositories.candidates import set_related_series

    set_related_series(db_session, cand.id, series.id)
    db_session.commit()

    def _db():
        yield db_session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app)
    form = {
        "from_view": "detail",
        "reviewer": "ui-tester",
        "title": "Título desde consola",
        "subtitle": "",
        "dek": "Bajada",
        "body_markdown": "## Sección\n\nCuerpo publicado vía UI.",
        "topic": "economy",
        "tags_csv": "macro, test-ui",
        "summary": "Resumen UI",
        "slug": "",
    }
    resp = client.post(f"/editorial/ui/candidates/{cand.id}/publish-web", data=form, follow_redirects=False)
    assert resp.status_code == 303, resp.text
    loc = resp.headers.get("location", "")
    assert "message=" in loc

    row = db_session.scalar(select(PublicStory).where(PublicStory.candidate_id == cand.id))
    assert row is not None
    assert row.status == "published"
    assert row.title == "Título desde consola"
    assert row.published_by == "ui-tester"
    assert row.topic == "economy"

    app.dependency_overrides.clear()


def test_public_api_filters_and_slug(db_session) -> None:
    now = datetime.now(UTC)
    a = StoryCandidate(
        title="A", insight="i", status="accepted", dedupe_hash="pub-a", suggested_chart_type="bar"
    )
    b = StoryCandidate(
        title="B", insight="j", status="accepted", dedupe_hash="pub-b", suggested_chart_type="line"
    )
    db_session.add_all([a, b])
    db_session.flush()
    db_session.add_all(
        [
            PublicStory(
                slug="story-a-1",
                title="A",
                subtitle=None,
                dek=None,
                body_markdown="x",
                topic="economy",
                tags=["macro"],
                primary_chart_spec={"type": "bar", "series": []},
                secondary_chart_spec=None,
                chart_type="bar",
                candidate_id=a.id,
                sources=None,
                summary=None,
                status="published",
                language="es",
                published_at=now,
                scheduled_at=None,
                published_by="editor",
                created_at=now,
                updated_at=now,
            ),
            PublicStory(
                slug="story-b-2",
                title="B",
                subtitle=None,
                dek=None,
                body_markdown="y",
                topic="housing",
                tags=["vivienda"],
                primary_chart_spec={"type": "line", "series": []},
                secondary_chart_spec=None,
                chart_type="line",
                candidate_id=b.id,
                sources=None,
                summary=None,
                status="draft",
                language="es",
                published_at=None,
                scheduled_at=None,
                published_by=None,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    db_session.commit()

    def _db():
        yield db_session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app)

    lst = client.get("/public/stories?page=1&page_size=10")
    assert lst.status_code == 200
    body = lst.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["slug"] == "story-a-1"
    assert "candidate_id" not in body["items"][0]

    detail = client.get("/public/stories/story-a-1")
    assert detail.status_code == 200
    d = detail.json()
    assert d["slug"] == "story-a-1"
    assert d["primary_chart_spec"]["type"] == "bar"
    assert "candidate_id" not in d
    assert "chart_public_caption" in d and isinstance(d["chart_public_caption"], str)
    assert "analysis_economic" in d and "analysis_social" in d
    assert isinstance(d.get("correlations"), list)

    assert client.get("/public/stories/nonexistent-slug").status_code == 404

    by_topic = client.get("/public/stories/by-topic/economy")
    assert by_topic.status_code == 200
    assert by_topic.json()["total"] == 1

    tagged = client.get("/public/stories?tag=macro")
    assert tagged.status_code == 200
    assert tagged.json()["total"] == 1

    app.dependency_overrides.clear()


def test_public_story_detail_correlates_secondary_series(db_session) -> None:
    source = Source(slug="corr-src", name="Corr", source_type="api", base_url="https://example.com")
    db_session.add(source)
    db_session.flush()
    s1 = Series(source_id=source.id, external_code="C1", name="Indicador principal", frequency="monthly")
    s2 = Series(source_id=source.id, external_code="C2", name="Indicador secundario", frequency="monthly")
    db_session.add_all([s1, s2])
    db_session.flush()
    for i in range(8):
        d = date(2024, 1 + i, 15)
        db_session.add(SeriesObservation(series_id=s1.id, obs_date=d, obs_value=Decimal(str(10 + i))))
        db_session.add(SeriesObservation(series_id=s2.id, obs_date=d, obs_value=Decimal(str(20 + i * 2))))
    cand = StoryCandidate(
        title="Historia correlacionada",
        insight="Lectura social.",
        executive_summary="Resumen ejecutivo.",
        why_it_matters="Por qué importa.",
        status="accepted",
        dedupe_hash="corr-detail-1",
        suggested_chart_type="line",
    )
    db_session.add(cand)
    db_session.flush()
    from app.editorial.repositories.candidates import set_related_series

    set_related_series(db_session, cand.id, s1.id)
    db_session.add(CandidateRelatedSeries(candidate_id=cand.id, series_id=s2.id, relation_type="context"))
    db_session.commit()

    def _db():
        yield db_session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app)
    payload = {
        "title": "Publicación correlación",
        "subtitle": None,
        "dek": None,
        "body_markdown": "Cuerpo **markdown**.",
        "topic": "economy",
        "tags": ["macro"],
        "chart_type": "line",
        "sources": [],
    }
    resp = client.post(f"/candidates/{cand.id}/publish", json=payload)
    assert resp.status_code == 200, resp.text
    slug = resp.json()["slug"]
    detail = client.get(f"/public/stories/{slug}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["chart_public_caption"]
    corrs = body["correlations"]
    assert len(corrs) >= 1
    assert any(c.get("coefficient") is not None for c in corrs)

    app.dependency_overrides.clear()
