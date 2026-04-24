from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models import Series, SeriesObservation, Source


def test_editorial_flow_end_to_end(db_session) -> None:
    source = Source(slug="e2e-source", name="E2E Source", source_type="api", base_url="https://example.com")
    db_session.add(source)
    db_session.flush()
    series = Series(source_id=source.id, external_code="E2E-1", name="Serie E2E", frequency="monthly")
    db_session.add(series)
    db_session.flush()
    for idx, value in enumerate([Decimal("100"), Decimal("101"), Decimal("99"), Decimal("120")]):
        db_session.add(
            SeriesObservation(
                series_id=series.id,
                obs_date=date(2025, idx + 1, 1),
                obs_value=value,
            )
        )
    db_session.commit()

    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    client = TestClient(app)

    run_resp = client.post("/candidates/run?limit_series=20")
    assert run_resp.status_code == 200

    candidates_resp = client.get("/candidates?limit=20")
    assert candidates_resp.status_code == 200
    candidates = candidates_resp.json()
    assert len(candidates) >= 1
    candidate_id = candidates[0]["id"]

    assert client.post(f"/candidates/{candidate_id}/score").status_code == 200
    assert client.post(f"/candidates/{candidate_id}/draft").status_code == 200
    assert client.post(f"/candidates/{candidate_id}/crosses").status_code == 200
    assert client.post(f"/candidates/{candidate_id}/shortlist").status_code == 200
    assert client.post(f"/candidates/{candidate_id}/approve").status_code == 200

    publish_body = {
        "title": candidates[0]["title"],
        "subtitle": "Resumen editorial",
        "dek": "Una línea de contexto.",
        "body_markdown": f"## Historia\n\n{candidates[0]['insight']}",
        "topic": "economy",
        "tags": ["e2e"],
    }
    publish_resp = client.post(f"/candidates/{candidate_id}/publish", json=publish_body)
    assert publish_resp.status_code == 200, publish_resp.text
    story_slug = publish_resp.json()["slug"]

    public_stories_resp = client.get("/public/stories?page=1&page_size=20")
    assert public_stories_resp.status_code == 200
    payload = public_stories_resp.json()
    assert payload["total"] >= 1
    assert any(item["slug"] == story_slug for item in payload["items"])

    public_story_detail_resp = client.get(f"/public/stories/{story_slug}")
    assert public_story_detail_resp.status_code == 200
    detail = public_story_detail_resp.json()
    assert detail["slug"] == story_slug
    assert "candidate_id" not in detail
    assert detail["body_markdown"]

    topic_resp = client.get("/public/stories/by-topic/economy?page=1&page_size=20")
    assert topic_resp.status_code == 200
    assert topic_resp.json()["total"] >= 1

    app.dependency_overrides.clear()
