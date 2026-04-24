from __future__ import annotations

import zlib
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session


def _lock_id(name: str) -> int:
    # Stable 32-bit key for pg advisory locks.
    return int(zlib.crc32(name.encode("utf-8")))


@contextmanager
def advisory_job_lock(db: Session, job_name: str) -> Generator[bool, None, None]:
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        yield True
        return

    lock_key = _lock_id(job_name)
    acquired = bool(db.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_key}).scalar())
    if not acquired:
        yield False
        return
    try:
        yield True
    finally:
        db.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": lock_key})


def lock_backend(db: Session) -> str:
    bind = db.get_bind()
    if bind is None:
        return "unknown"
    if bind.dialect.name == "postgresql":
        return "postgresql_advisory_lock"
    return "in_memory_noop"
