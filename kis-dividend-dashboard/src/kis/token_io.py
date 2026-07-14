"""Token endpoint and process-memory adapters isolated from reuse policy."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from http import HTTPStatus
from typing import TYPE_CHECKING

import requests
from pydantic import BaseModel, ConfigDict, ValidationError

if TYPE_CHECKING:
    from src.repositories.tokens import TokenIdentity


class TokenAcquisitionSource(StrEnum):
    """Safe source metadata displayed without exposing the token value."""

    MEMORY = "memory"
    DATABASE = "database"
    ISSUED = "issued"


@dataclass(frozen=True, slots=True)
class TokenResponse:
    """Validated token endpoint response used by the policy layer."""

    access_token: str = field(repr=False)
    token_type: str
    expires_in: int
    access_token_token_expired: str | None


@dataclass(frozen=True, slots=True)
class TokenAcquisition:
    """Usable token plus non-secret reuse metadata."""

    access_token: str = field(repr=False)
    token_type: str
    expires_at: datetime
    source: TokenAcquisitionSource
    near_expiry: bool


class TokenPolicyError(RuntimeError):
    """Base error that deliberately contains no secret response material."""


class DemoModeTokenAccessError(TokenPolicyError):
    """Raised before any database or network access in demo mode."""


class TokenIssuanceBlockedError(TokenPolicyError):
    """Raised when durable rate-limit metadata forbids issuance."""


class TokenDecryptionError(TokenPolicyError):
    """Raised when stored ciphertext cannot be decrypted safely."""


class TokenAuthenticationError(TokenPolicyError):
    """Raised for invalid App Key or App Secret responses without retry."""


class TokenRateLimitError(TokenPolicyError):
    """Raised for provider rate-limit responses without retry."""


class TokenNetworkError(TokenPolicyError):
    """Raised for transient transport errors eligible for one retry."""


class TokenResponseError(TokenPolicyError):
    """Raised when provider response fields fail strict validation."""


class _TokenPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    access_token: str
    token_type: str
    expires_in: int
    access_token_token_expired: str | None = None


class HttpTokenIssuer:
    """Read-only OAuth client with mandatory timeout and redacted failures."""

    def __init__(
        self,
        *,
        base_url: str,
        app_key: str,
        app_secret: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        """Retain credentials only inside the server-side HTTP adapter."""
        self._url = f"{base_url.rstrip('/')}/oauth2/tokenP"
        self._app_key = app_key
        self._app_secret = app_secret
        self._timeout_seconds = timeout_seconds

    def issue(self) -> TokenResponse:
        """Call the token endpoint without logging credentials or response bodies."""
        try:
            response = requests.post(
                self._url,
                json={
                    "grant_type": "client_credentials",
                    "appkey": self._app_key,
                    "appsecret": self._app_secret,
                },
                headers={"content-type": "application/json"},
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as error:
            msg = "KIS token endpoint network failure"
            raise TokenNetworkError(msg) from error
        if response.status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}:
            msg = "KIS token authentication failed"
            raise TokenAuthenticationError(msg)
        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            msg = "KIS token issuance is rate limited"
            raise TokenRateLimitError(msg)
        if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            msg = "KIS token endpoint is temporarily unavailable"
            raise TokenNetworkError(msg)
        if not response.ok:
            msg = "KIS token endpoint rejected the request"
            raise TokenResponseError(msg)
        try:
            payload = _TokenPayload.model_validate(response.json())
        except (requests.JSONDecodeError, ValidationError) as error:
            msg = "KIS token response validation failed"
            raise TokenResponseError(msg) from error
        return TokenResponse(
            payload.access_token,
            payload.token_type,
            payload.expires_in,
            payload.access_token_token_expired,
        )


class InMemoryTokenStore:
    """Process-local optimization; PostgreSQL remains the durable authority."""

    def __init__(self) -> None:
        """Create an empty process-local store guarded for Streamlit threads."""
        self._tokens: dict[TokenIdentity, TokenAcquisition] = {}
        self._lock = threading.RLock()

    def get(self, identity: TokenIdentity) -> TokenAcquisition | None:
        """Read one process-local token."""
        with self._lock:
            return self._tokens.get(identity)

    def put(self, identity: TokenIdentity, token: TokenAcquisition) -> None:
        """Store one process-local token without serialization."""
        with self._lock:
            self._tokens[identity] = token


class SystemClock:
    """Production clock implementation."""

    def now_utc(self) -> datetime:
        """Return the current UTC instant."""
        return datetime.now(UTC)
