from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models import Series, SeriesObservation, Source


def test_signals_simulate_endpoint(db_session) -> None:
    source = Source(slug="sim-test", name="Sim test", source_type="api", base_url="https://example.com")
    db_session.add(source)
    db_session.flush()
    series = Series(source_id=source.id, external_code="SIM1", name="Serie simulada", frequency="monthly")
    db_session.add(series)
    db_session.flush()
    for idx, value in enumerate([Decimal("100"), Decimal("101"), Decimal("102"), Decimal("120")]):
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
    response = client.post(f"/signals/simulate?series_id={series.id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["series_id"] == series.id
    assert payload["signals_count"] >= 1
    app.dependency_overrides.clear()
