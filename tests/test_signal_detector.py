from datetime import date
from decimal import Decimal

from app.editorial.services.signal_detector import run_signal_detection
from app.models import Series, SeriesObservation, Source


def test_signal_detector_creates_strong_change_signal(db_session) -> None:
    source = Source(slug="ine-test", name="INE test", source_type="api", base_url="https://example.com")
    db_session.add(source)
    db_session.flush()
    series = Series(source_id=source.id, external_code="S1", name="Serie test", frequency="monthly")
    db_session.add(series)
    db_session.flush()
    values = [Decimal("100"), Decimal("102"), Decimal("101"), Decimal("120")]
    for idx, value in enumerate(values):
        db_session.add(
            SeriesObservation(
                series_id=series.id,
                obs_date=date(2025, idx + 1, 1),
                obs_value=value,
            )
        )
    db_session.commit()

    signals = run_signal_detection(db_session, limit_series=10)
    assert len(signals) >= 1
    assert any(s.signal_type == "strong_period_change" for s in signals)
