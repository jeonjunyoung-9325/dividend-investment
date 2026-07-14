"""SQLAlchemy engine and transaction factories for PostgreSQL production storage."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Final

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.engine.interfaces import DBAPIConnection
    from sqlalchemy.pool import ConnectionPoolEntry

DATABASE_SCHEMA: Final = "kis_dashboard"


def normalize_database_url(database_url: str) -> str:
    """Select the psycopg driver while preserving provider connection parameters."""
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


def _set_dashboard_search_path(
    dbapi_connection: DBAPIConnection,
    _connection_record: ConnectionPoolEntry,
) -> None:
    previous_autocommit = dbapi_connection.autocommit
    dbapi_connection.autocommit = True
    try:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"SET SESSION search_path TO {DATABASE_SCHEMA}")
        finally:
            cursor.close()
    finally:
        dbapi_connection.autocommit = previous_autocommit


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create a production-safe engine or a shared in-memory SQLite test engine."""
    normalized = normalize_database_url(database_url)
    if normalized.startswith("sqlite") and ":memory:" in normalized:
        return create_engine(
            normalized,
            echo=echo,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    engine = create_engine(normalized, echo=echo, pool_pre_ping=True, pool_recycle=300)
    event.listen(engine, "connect", _set_dashboard_search_path, insert=True)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return sessions whose loaded values remain usable after commit."""
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Commit a unit of work and always close its connection."""
    with factory() as session, session.begin():
        yield session
