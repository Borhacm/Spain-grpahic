from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.editorial.models import CandidateSignal, SignalRule
from app.editorial.services.candidate_service import run_signal_pipeline
from app.models import Series, SeriesObservation, Source


def test_run_signal_pipeline_persists_rule_id_for_rule_based_signal(db_session) -> None:
    source = Source(slug="trace-source", name="Trace Source", source_type="api", base_url="https://example.com")
    db_session.add(source)
    db_session.flush()

    rule = SignalRule(
        slug="rule-strong-period-change",
        name="Strong Period Change",
        signal_type="strong_period_change",
        params_json={"mom_threshold_pct": 5},
        weight=Decimal("1.0"),
        enabled=True,
    )
    db_session.add(rule)
    db_session.flush()

    series = Series(source_id=source.id, external_code="TRACE-1", name="Serie Trace", frequency="monthly")
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

    result = run_signal_pipeline(db_session, limit_series=20)
    db_session.commit()

    assert result["signals_written"] >= 1
    signal = db_session.scalar(
        select(CandidateSignal)
        .where(CandidateSignal.signal_type == "strong_period_change")
        .order_by(CandidateSignal.id.desc())
    )
    assert signal is not None
    assert signal.rule_id == rule.id
