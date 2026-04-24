import os
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.job_lock import advisory_job_lock
from app.editorial.models import CandidateSignal, StoryCandidate


def _postgres_url() -> str | None:
    value = os.getenv("DATABASE_URL")
    if value and value.startswith("postgresql"):
        return value
    return None


@pytest.fixture
def postgres_session() -> Session:
    url = _postgres_url()
    if not url:
        pytest.skip("Postgres integration test requires DATABASE_URL=postgresql...")
    engine = create_engine(url, future=True)
    connection = engine.connect()
    tx = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        tx.rollback()
        connection.close()
        engine.dispose()


@pytest.fixture
def postgres_second_session() -> Session:
    url = _postgres_url()
    if not url:
        pytest.skip("Postgres integration test requires DATABASE_URL=postgresql...")
    engine = create_engine(url, future=True)
    connection = engine.connect()
    tx = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        tx.rollback()
        connection.close()
        engine.dispose()


def test_advisory_lock_blocks_second_session(postgres_session: Session, postgres_second_session: Session) -> None:
    with advisory_job_lock(postgres_session, "integration_lock_test") as locked_first:
        assert locked_first is True
        with advisory_job_lock(postgres_second_session, "integration_lock_test") as locked_second:
            assert locked_second is False


def test_candidate_signal_unique_constraint(postgres_session: Session) -> None:
    candidate = StoryCandidate(
        title="Integration candidate",
        insight="integration",
        executive_summary=None,
        why_it_matters=None,
        geography=None,
        period_label="2026-04",
        status="new",
        dedupe_hash=f"int-{datetime.now(UTC).timestamp()}",
    )
    postgres_session.add(candidate)
    postgres_session.flush()

    first = CandidateSignal(
        candidate_id=candidate.id,
        signal_type="integration",
        signal_key="same-key",
        explanation="first",
        strength=Decimal("1"),
    )
    second = CandidateSignal(
        candidate_id=candidate.id,
        signal_type="integration",
        signal_key="same-key",
        explanation="second",
        strength=Decimal("2"),
    )
    postgres_session.add(first)
    postgres_session.flush()
    postgres_session.add(second)
    with pytest.raises(IntegrityError):
        postgres_session.flush()
    postgres_session.rollback()
