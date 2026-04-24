from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models import Series, SeriesObservation, Source


def test_public_country_overview_returns_dashboard_payload(db_session) -> None:
    def _db():
        yield db_session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app)
    response = client.get("/public/country-overview")
    assert response.status_code == 200, response.text

    payload = response.json()
    assert isinstance(payload.get("executive_kpis"), list)
    assert len(payload["executive_kpis"]) >= 6
    assert isinstance(payload.get("executive_narrative"), list)
    assert isinstance(payload.get("sections"), list)
    assert len(payload["sections"]) >= 4

    first_kpi = payload["executive_kpis"][0]
    assert "id" in first_kpi and "value" in first_kpi
    app.dependency_overrides.clear()


def test_public_country_overview_mapping_status(db_session, monkeypatch) -> None:
    source = Source(slug="ine", name="Instituto Nacional de Estadistica", source_type="api", base_url="https://example.com")
    db_session.add(source)
    db_session.flush()

    series = Series(source_id=source.id, external_code="IPC_TEST", name="IPC test", frequency="monthly")
    db_session.add(series)
    db_session.flush()
    db_session.add(SeriesObservation(series_id=series.id, obs_date=date(2025, 1, 1), obs_value=2.5))
    db_session.commit()

    monkeypatch.setenv("COUNTRY_OVERVIEW_SERIES_MAP", "inflation=ine:IPC_TEST,gdp=bde:NOPE")

    def _db():
        yield db_session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app)
    response = client.get("/public/country-overview/mapping-status")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["configured_mappings"] == 2
    assert payload["resolved_mappings"] == 1
    assert any(item["indicator_id"] == "inflation" and item["mapped"] for item in payload["items"])
    assert any(item["indicator_id"] == "gdp" and not item["mapped"] for item in payload["items"])
    app.dependency_overrides.clear()


def test_public_country_overview_strict_mode_returns_422_on_unresolved_mapping(db_session, monkeypatch) -> None:
    monkeypatch.setenv("COUNTRY_OVERVIEW_SERIES_MAP", "inflation=ine:MISSING_SERIES")

    def _db():
        yield db_session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app)
    response = client.get("/public/country-overview?strict=true")
    assert response.status_code == 422, response.text
    payload = response.json()
    assert payload["detail"]["code"] == "country_overview_mapping_incomplete"
    assert len(payload["detail"]["failures"]) == 1
    assert payload["detail"]["failures"][0]["indicator_id"] == "inflation"
    app.dependency_overrides.clear()
