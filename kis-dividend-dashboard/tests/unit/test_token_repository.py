from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.models import Base
from src.repositories.tokens import StoredToken, TokenIdentity, TokenRepository


def _repository() -> TokenRepository:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return TokenRepository(sessionmaker(engine, expire_on_commit=False))


def test_repository_round_trip_keeps_only_ciphertext() -> None:
    repository = _repository()
    identity = TokenIdentity(environment="real", app_key_fingerprint="a" * 64)
    issued_at = datetime(2026, 7, 14, tzinfo=UTC)

    with repository.issuance_lock(identity, timeout_seconds=1) as locked:
        locked.save_success(
            identity=identity,
            token=StoredToken(
                encrypted_access_token=b"ciphertext-only",
                token_type="Bearer",  # noqa: S106
                issued_at=issued_at,
                expires_at=issued_at + timedelta(hours=24),
                requested_at=issued_at,
            ),
        )

    stored = repository.get(identity)
    assert stored is not None
    assert stored.encrypted_access_token == b"ciphertext-only"
    assert stored.state == "usable"


def test_repository_failure_metadata_survives_transaction() -> None:
    repository = _repository()
    identity = TokenIdentity(environment="demo", app_key_fingerprint="b" * 64)
    requested_at = datetime(2026, 7, 14, tzinfo=UTC)

    with repository.issuance_lock(identity, timeout_seconds=1) as locked:
        locked.mark_requesting(identity, requested_at=requested_at)
        locked.mark_failure(
            identity,
            failure_kind="network",
            failed_at=requested_at,
            blocked_until=requested_at + timedelta(minutes=5),
        )

    stored = repository.get(identity)
    assert stored is not None
    assert stored.state == "request_failed"
    assert stored.last_requested_at == requested_at
    assert stored.last_failure_kind == "network"
