from __future__ import annotations

import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from typing import TYPE_CHECKING, Final

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from src.models import SyncRun

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.orm import Session, sessionmaker

SYNC_LOCK_SCOPE: Final = "kis-dashboard:portfolio-sync"
_LOCAL_LOCK = threading.Lock()


class SyncLockTimeoutError(RuntimeError):
    pass


@contextmanager
def synchronization_lock(
    session_factory: sessionmaker[Session], *, timeout_seconds: int = 5
) -> Iterator[None]:
    with session_factory() as session, session.begin():
        if session.bind is not None and session.bind.dialect.name == "postgresql":
            session.execute(text(f"SET LOCAL lock_timeout = '{max(1, timeout_seconds) * 1000}ms'"))
            key = int.from_bytes(sha256(SYNC_LOCK_SCOPE.encode()).digest()[:8], "big", signed=True)
            try:
                session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
            except (TimeoutError, DBAPIError) as error:
                raise SyncLockTimeoutError from error
            yield
            return
        if not _LOCAL_LOCK.acquire(timeout=timeout_seconds):
            raise SyncLockTimeoutError
        try:
            yield
        finally:
            _LOCAL_LOCK.release()


def start_run(session: Session, *, started_at: datetime | None = None) -> SyncRun:
    run = SyncRun(started_at=started_at or datetime.now(UTC), status="running")
    session.add(run)
    session.flush()
    return run


def latest_run(session: Session, *, successful_only: bool = False) -> SyncRun | None:
    statement = select(SyncRun)
    if successful_only:
        statement = statement.where(SyncRun.status.in_(("success", "partial")))
    return session.scalar(statement.order_by(SyncRun.started_at.desc()).limit(1))
