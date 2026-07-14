"""KIS access-token issuance, encryption, persistence, and reuse policy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Protocol, assert_never
from zoneinfo import ZoneInfo

from cryptography.fernet import InvalidToken

from src.kis.token_io import (
    DemoModeTokenAccessError,
    HttpTokenIssuer,
    InMemoryTokenStore,
    SystemClock,
    TokenAcquisition,
    TokenAcquisitionSource,
    TokenAuthenticationError,
    TokenDecryptionError,
    TokenIssuanceBlockedError,
    TokenNetworkError,
    TokenPolicyError,
    TokenRateLimitError,
    TokenResponse,
    TokenResponseError,
)
from src.repositories.tokens import StoredToken

__all__ = [
    "DemoModeTokenAccessError",
    "HttpTokenIssuer",
    "InMemoryTokenStore",
    "SystemClock",
    "TokenAcquisition",
    "TokenAcquisitionSource",
    "TokenAuthenticationError",
    "TokenDecryptionError",
    "TokenIssuanceBlockedError",
    "TokenManager",
    "TokenNetworkError",
    "TokenRateLimitError",
    "TokenResponse",
    "TokenResponseError",
]

if TYPE_CHECKING:
    from src.models import KisTokenCache
    from src.repositories.tokens import TokenIdentity, TokenRepository
    from src.security import TokenCipher


class TokenIssuer(Protocol):
    """Narrow external token endpoint boundary."""

    def issue(self) -> TokenResponse:
        """Issue or retrieve the provider token exactly once per call."""
        ...


class Clock(Protocol):
    """Injectable UTC clock for deterministic expiry tests."""

    def now_utc(self) -> datetime:
        """Return a timezone-aware UTC instant."""
        ...


class TokenManager:
    """Apply memory, database, expiry, locking, and limited-retry policy."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        repository: TokenRepository,
        cipher: TokenCipher,
        issuer: TokenIssuer,
        clock: Clock,
        memory: InMemoryTokenStore,
        expiry_buffer: timedelta,
        demo_mode: bool,
        lock_timeout_seconds: int = 5,
        minimum_reissue_interval: timedelta = timedelta(hours=6),
    ) -> None:
        """Bind policy dependencies and official issuance timing controls."""
        self._repository = repository
        self._cipher = cipher
        self._issuer = issuer
        self._clock = clock
        self._memory = memory
        self._expiry_buffer = expiry_buffer
        self._demo_mode = demo_mode
        self._lock_timeout_seconds = lock_timeout_seconds
        self._minimum_reissue_interval = minimum_reissue_interval

    def get_access_token(self, identity: TokenIdentity) -> TokenAcquisition:
        """Reuse a valid token or issue once under the distributed lock."""
        if self._demo_mode:
            msg = "Token access is disabled in demo mode"
            raise DemoModeTokenAccessError(msg)
        now = self._clock.now_utc()
        memory_token = self._memory.get(identity)
        if memory_token is not None and self._is_preferred_valid(memory_token.expires_at, now):
            return TokenAcquisition(
                memory_token.access_token,
                memory_token.token_type,
                memory_token.expires_at,
                TokenAcquisitionSource.MEMORY,
                near_expiry=False,
            )
        database_token = self._from_record(self._repository.get(identity), now)
        if database_token is not None and not database_token.near_expiry:
            self._memory.put(identity, database_token)
            return database_token
        outcome = self._acquire_under_lock(identity, now)
        match outcome:
            case TokenAcquisition():
                self._memory.put(identity, outcome)
                return outcome
            case TokenPolicyError():
                raise outcome
            case unreachable:
                assert_never(unreachable)

    def _acquire_under_lock(
        self, identity: TokenIdentity, now: datetime
    ) -> TokenAcquisition | TokenPolicyError:
        with self._repository.issuance_lock(
            identity, timeout_seconds=self._lock_timeout_seconds
        ) as locked:
            record = locked.get(identity)
            locked_token = self._from_record(record, now)
            if locked_token is not None and not locked_token.near_expiry:
                return locked_token
            invalid_cipher = self._cipher_is_invalid(record)
            if invalid_cipher:
                locked.mark_decryption_failed(identity, failed_at=now)
            blocked = self._blocked_outcome(
                record, locked_token, now, invalid_cipher=invalid_cipher
            )
            if blocked is not None:
                return blocked
            locked.mark_requesting(identity, requested_at=now)
            try:
                response = self._issue_with_limited_retry()
                expires_at = self._response_expiry(response, now)
                encrypted = self._cipher.encrypt(response.access_token)
                locked.save_success(
                    identity=identity,
                    token=StoredToken(
                        encrypted_access_token=encrypted,
                        token_type=response.token_type,
                        issued_at=now,
                        expires_at=expires_at,
                        requested_at=now,
                    ),
                )
            except TokenPolicyError as error:
                blocked_until = now + self._failure_cooldown(error)
                locked.mark_failure(
                    identity,
                    failure_kind=type(error).__name__,
                    failed_at=now,
                    blocked_until=blocked_until,
                )
                if locked_token is not None and locked_token.expires_at > now:
                    return locked_token
                return error
        return TokenAcquisition(
            response.access_token,
            response.token_type,
            expires_at,
            TokenAcquisitionSource.ISSUED,
            near_expiry=False,
        )

    def _from_record(self, record: KisTokenCache | None, now: datetime) -> TokenAcquisition | None:
        if record is None:
            return None
        if (
            record.encrypted_access_token is None
            or record.token_type is None
            or record.expires_at is None
            or record.expires_at <= now
        ):
            return None
        try:
            plaintext = self._cipher.decrypt(record.encrypted_access_token)
        except InvalidToken:
            return None
        return TokenAcquisition(
            plaintext,
            record.token_type,
            record.expires_at,
            TokenAcquisitionSource.DATABASE,
            not self._is_preferred_valid(record.expires_at, now),
        )

    def _cipher_is_invalid(self, record: KisTokenCache | None) -> bool:
        if record is None or record.encrypted_access_token is None:
            return False
        try:
            self._cipher.decrypt(record.encrypted_access_token)
        except InvalidToken:
            return True
        return False

    def _blocked_outcome(
        self,
        record: KisTokenCache | None,
        fallback: TokenAcquisition | None,
        now: datetime,
        *,
        invalid_cipher: bool,
    ) -> TokenAcquisition | TokenPolicyError | None:
        if record is None:
            return None
        if record.blocked_until is not None and record.blocked_until > now:
            return fallback or TokenIssuanceBlockedError("Token issuance is temporarily blocked")
        if (
            record.last_requested_at is not None
            and now - record.last_requested_at < self._minimum_reissue_interval
        ):
            if fallback is not None:
                return fallback
            if invalid_cipher:
                return TokenDecryptionError("Stored token cannot be decrypted")
            return TokenIssuanceBlockedError("Token issuance is inside the provider reuse window")
        return None

    def _is_preferred_valid(self, expires_at: datetime, now: datetime) -> bool:
        return now < expires_at - self._expiry_buffer

    def _issue_with_limited_retry(self) -> TokenResponse:
        try:
            return self._issuer.issue()
        except TokenNetworkError:
            return self._issuer.issue()

    def _response_expiry(self, response: TokenResponse, issued_at: datetime) -> datetime:
        if response.access_token_token_expired:
            try:
                parsed = datetime.fromisoformat(response.access_token_token_expired)
            except ValueError as error:
                msg = "KIS token expiry timestamp is invalid"
                raise TokenResponseError(msg) from error
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=ZoneInfo("Asia/Seoul"))
            return parsed.astimezone(UTC)
        if response.expires_in <= 0:
            msg = "KIS token expiry duration is invalid"
            raise TokenResponseError(msg)
        return issued_at + timedelta(seconds=response.expires_in)

    def _failure_cooldown(self, error: TokenPolicyError) -> timedelta:
        if isinstance(error, TokenNetworkError):
            return timedelta(minutes=5)
        return self._minimum_reissue_interval
