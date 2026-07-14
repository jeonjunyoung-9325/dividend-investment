from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.kis.auth import (
    DemoModeTokenAccessError,
    InMemoryTokenStore,
    TokenAcquisitionSource,
    TokenManager,
    TokenResponse,
)
from src.models import Base
from src.repositories.tokens import StoredToken, TokenIdentity, TokenRepository
from src.security import TokenCipher


@dataclass(frozen=True, slots=True)
class FixedClock:
    current: datetime

    def now_utc(self) -> datetime:
        return self.current


class FakeIssuer:
    def __init__(self, response: TokenResponse) -> None:
        self.response = response
        self.calls = 0

    def issue(self) -> TokenResponse:
        self.calls += 1
        return self.response


def _repository() -> TokenRepository:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return TokenRepository(sessionmaker(engine, expire_on_commit=False))


def test_manager_reuses_database_token_after_memory_restart() -> None:
    now = datetime(2026, 7, 14, tzinfo=UTC)
    repository = _repository()
    identity = TokenIdentity(environment="real", app_key_fingerprint="c" * 64)
    cipher = TokenCipher(Fernet.generate_key().decode("ascii"))
    with repository.issuance_lock(identity, timeout_seconds=1) as locked:
        locked.save_success(
            identity=identity,
            token=StoredToken(
                encrypted_access_token=cipher.encrypt("database-token"),
                token_type="Bearer",  # noqa: S106
                issued_at=now - timedelta(hours=1),
                expires_at=now + timedelta(hours=23),
                requested_at=now - timedelta(hours=1),
            ),
        )
    issuer = FakeIssuer(TokenResponse("new-token", "Bearer", 86_400, None))
    manager = TokenManager(
        repository=repository,
        cipher=cipher,
        issuer=issuer,
        clock=FixedClock(now),
        memory=InMemoryTokenStore(),
        expiry_buffer=timedelta(minutes=5),
        demo_mode=False,
    )

    acquired = manager.get_access_token(identity)

    assert acquired.access_token == "database-token"  # noqa: S105
    assert acquired.source is TokenAcquisitionSource.DATABASE
    assert issuer.calls == 0


def test_manager_issues_once_then_reuses_memory() -> None:
    now = datetime(2026, 7, 14, tzinfo=UTC)
    issuer = FakeIssuer(TokenResponse("issued-token", "Bearer", 86_400, None))
    manager = TokenManager(
        repository=_repository(),
        cipher=TokenCipher(Fernet.generate_key().decode("ascii")),
        issuer=issuer,
        clock=FixedClock(now),
        memory=InMemoryTokenStore(),
        expiry_buffer=timedelta(minutes=5),
        demo_mode=False,
    )
    identity = TokenIdentity(environment="demo", app_key_fingerprint="d" * 64)

    first = manager.get_access_token(identity)
    second = manager.get_access_token(identity)

    assert first.source is TokenAcquisitionSource.ISSUED
    assert second.source is TokenAcquisitionSource.MEMORY
    assert issuer.calls == 1


def test_demo_mode_never_reads_repository_or_calls_issuer() -> None:
    issuer = FakeIssuer(TokenResponse("must-not-be-used", "Bearer", 86_400, None))
    manager = TokenManager(
        repository=_repository(),
        cipher=TokenCipher(Fernet.generate_key().decode("ascii")),
        issuer=issuer,
        clock=FixedClock(datetime(2026, 7, 14, tzinfo=UTC)),
        memory=InMemoryTokenStore(),
        expiry_buffer=timedelta(minutes=5),
        demo_mode=True,
    )

    with pytest.raises(DemoModeTokenAccessError):
        manager.get_access_token(TokenIdentity("real", "e" * 64))

    assert issuer.calls == 0
