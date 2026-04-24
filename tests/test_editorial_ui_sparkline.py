"""Lazy sparkline JSON + chart fields on API candidates."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models import Series, SeriesObservation, Source
from app.editorial.models import CandidateSignal, StoryCandidate


def test_signal_chart_data_ok(db_session) -> None:
    source = Source(slug="spark-src", name="Spark Src", source_type="api", base_url="https://example.com")
    db_session.add(source)
    db_session.flush()
    series = Series(source_id=source.id, external_code="S-1", name="Serie 1", frequency="monthly")
    db_session.add(series)
    db_session.flush()
    for idx, value in enumerate([Decimal("1"), Decimal("2"), Decimal("3")]):
        db_session.add(
            SeriesObservation(series_id=series.id, obs_date=date(2025, 1, idx + 1), obs_value=value)
        )
    cand = StoryCandidate(
        title="T",
        insight="I",
        dedupe_hash="hash-spark-1",
        status="new",
    )
    db_session.add(cand)
    db_session.flush()
    sig = CandidateSignal(
        candidate_id=cand.id,
        signal_type="test",
        signal_key="k1",
        explanation="e",
        strength=Decimal("1"),
        payload_json={"series_id": series.id},
    )
    db_session.add(sig)
    db_session.commit()

    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)
    resp = client.get(f"/editorial/ui/signals/{sig.id}/chart-data")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "ok"
    assert data["series_label"] == "S-1 - Serie 1"
    assert data["payload"]["labels"]
    assert len(data["payload"]["values"]) >= 3


def test_signal_chart_data_na(db_session) -> None:
    cand = StoryCandidate(title="T2", insight="I2", dedupe_hash="hash-spark-2", status="new")
    db_session.add(cand)
    db_session.flush()
    sig = CandidateSignal(
        candidate_id=cand.id,
        signal_type="test",
        signal_key="k2",
        explanation="e",
        strength=Decimal("1"),
        payload_json={},
    )
    db_session.add(sig)
    db_session.commit()

    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)
    resp = client.get(f"/editorial/ui/signals/{sig.id}/chart-data")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["state"] == "na"


def test_candidate_out_includes_chart_fields(db_session) -> None:
    cand = StoryCandidate(
        title="T3",
        insight="I3",
        dedupe_hash="hash-spark-3",
        status="new",
        suggested_chart_type="line",
        chart_rationale="Porque si",
        chart_spec_json={"chart_rationale": "Porque si", "chart_policy": "topic_default_v2"},
    )
    db_session.add(cand)
    db_session.commit()

    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)
    resp = client.get(f"/candidates/{cand.id}")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["suggested_chart_type"] == "line"
    assert body["chart_type_suggested"] == "line"
    assert body["chart_rationale"] == "Porque si"
    assert body["chart_spec_json"]["chart_policy"] == "topic_default_v2"
