"""Persistent encrypted token state and cross-process issuance locking."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import TYPE_CHECKING, Final, Literal

from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from src.models import KisTokenCache

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.orm import Session, sessionmaker

TokenEnvironment = Literal["real", "demo"]
FINGERPRINT_LENGTH: Final = 64


@dataclass(frozen=True, slots=True)
class TokenIdentity:
    """Non-secret identity separating real/demo and distinct App Keys."""

    environment: TokenEnvironment
    app_key_fingerprint: str

    def __post_init__(self) -> None:
        """Reject malformed identities before they reach lock-key generation."""
        if len(self.app_key_fingerprint) != FINGERPRINT_LENGTH:
            msg = "App Key fingerprint must contain 64 hexadecimal characters"
            raise ValueError(msg)
        try:
            int(self.app_key_fingerprint, 16)
        except ValueError as error:
            msg = "App Key fingerprint must contain 64 hexadecimal characters"
            raise ValueError(msg) from error

    @property
    def lock_scope(self) -> str:
        """Return the stable distributed-lock namespace."""
        return f"kis-token:{self.environment}:{self.app_key_fingerprint}"


class TokenLockTimeoutError(RuntimeError):
    """Raised without issuing when the token lock cannot be acquired in time."""


@dataclass(frozen=True, slots=True)
class StoredToken:
    """Encrypted token values written as one consistent success transition."""

    encrypted_access_token: bytes
    token_type: str
    issued_at: datetime
    expires_at: datetime
    requested_at: datetime


_SQLITE_LOCKS: dict[str, threading.RLock] = {}
_SQLITE_LOCKS_GUARD = threading.Lock()


def _as_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_datetimes(row: KisTokenCache | None) -> KisTokenCache | None:
    if row is None:
        return None
    row.issued_at = _as_aware_utc(row.issued_at)
    row.expires_at = _as_aware_utc(row.expires_at)
    row.last_requested_at = _as_aware_utc(row.last_requested_at)
    row.request_lease_until = _as_aware_utc(row.request_lease_until)
    row.blocked_until = _as_aware_utc(row.blocked_until)
    row.last_failure_at = _as_aware_utc(row.last_failure_at)
    return row


class LockedTokenRepository:
    """Token mutations restricted to an acquired issuance lock."""

    def __init__(self, session: Session) -> None:
        """Bind mutations to the transaction holding the advisory lock."""
        self._session = session

    def get(self, identity: TokenIdentity) -> KisTokenCache | None:
        """Read and lock the token row when it exists."""
        statement = select(KisTokenCache).where(
            KisTokenCache.environment == identity.environment,
            KisTokenCache.app_key_fingerprint == identity.app_key_fingerprint,
        )
        if self._session.bind is not None and self._session.bind.dialect.name == "postgresql":
            statement = statement.with_for_update()
        return _normalize_datetimes(self._session.scalar(statement))

    def mark_requesting(self, identity: TokenIdentity, *, requested_at: datetime) -> None:
        """Persist the fact that the external issuance endpoint is about to be called."""
        row = self._get_or_create(identity)
        row.state = "requesting"
        row.last_requested_at = requested_at
        row.request_lease_until = requested_at + timedelta(minutes=2)
        row.last_failure_kind = None
        row.last_failure_at = None

    def save_success(
        self,
        *,
        identity: TokenIdentity,
        token: StoredToken,
    ) -> None:
        """Atomically replace token metadata after successful encrypted storage."""
        row = self._get_or_create(identity)
        row.encrypted_access_token = token.encrypted_access_token
        row.token_type = token.token_type
        row.issued_at = token.issued_at
        row.expires_at = token.expires_at
        row.last_requested_at = token.requested_at
        row.state = "usable"
        row.request_lease_until = None
        row.blocked_until = None
        row.last_failure_kind = None
        row.last_failure_at = None

    def mark_failure(
        self,
        identity: TokenIdentity,
        *,
        failure_kind: str,
        failed_at: datetime,
        blocked_until: datetime,
    ) -> None:
        """Keep a safe failure state without deleting the last encrypted token."""
        row = self._get_or_create(identity)
        row.state = "request_failed"
        row.request_lease_until = None
        row.blocked_until = blocked_until
        row.last_failure_kind = failure_kind
        row.last_failure_at = failed_at

    def mark_decryption_failed(self, identity: TokenIdentity, *, failed_at: datetime) -> None:
        """Invalidate unusable ciphertext without exposing or deleting it."""
        row = self._get_or_create(identity)
        row.state = "decrypt_failed"
        row.last_failure_kind = "decryption"
        row.last_failure_at = failed_at

    def _get_or_create(self, identity: TokenIdentity) -> KisTokenCache:
        row = self.get(identity)
        if row is not None:
            return row
        row = KisTokenCache(
            environment=identity.environment,
            app_key_fingerprint=identity.app_key_fingerprint,
            state="empty",
        )
        self._session.add(row)
        self._session.flush()
        return row


class TokenRepository:
    """Repository that owns transactions and PostgreSQL advisory locks."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Retain the application session factory for short units of work."""
        self._session_factory = session_factory

    def get(self, identity: TokenIdentity) -> KisTokenCache | None:
        """Return the current encrypted cache row without acquiring an issue lock."""
        with self._session_factory() as session:
            statement = select(KisTokenCache).where(
                KisTokenCache.environment == identity.environment,
                KisTokenCache.app_key_fingerprint == identity.app_key_fingerprint,
            )
            return _normalize_datetimes(session.scalar(statement))

    @contextmanager
    def issuance_lock(
        self, identity: TokenIdentity, *, timeout_seconds: int
    ) -> Iterator[LockedTokenRepository]:
        """Serialize issuance across processes and commit all resulting metadata."""
        with self._session_factory() as session, session.begin():
            sqlite_lock: threading.RLock | None = None
            if session.bind is not None and session.bind.dialect.name == "postgresql":
                milliseconds = max(1, timeout_seconds * 1000)
                session.execute(text(f"SET LOCAL lock_timeout = '{milliseconds}ms'"))
                lock_key = int.from_bytes(
                    sha256(identity.lock_scope.encode("utf-8")).digest()[:8],
                    byteorder="big",
                    signed=True,
                )
                try:
                    session.execute(
                        text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": lock_key}
                    )
                except OperationalError as error:
                    if getattr(error.orig, "sqlstate", None) == "55P03":
                        raise TokenLockTimeoutError from error
                    raise
                except TimeoutError as error:
                    raise TokenLockTimeoutError from error
            else:
                with _SQLITE_LOCKS_GUARD:
                    sqlite_lock = _SQLITE_LOCKS.setdefault(identity.lock_scope, threading.RLock())
                if not sqlite_lock.acquire(timeout=timeout_seconds):
                    raise TokenLockTimeoutError
            try:
                yield LockedTokenRepository(session)
            finally:
                if sqlite_lock is not None:
                    sqlite_lock.release()
