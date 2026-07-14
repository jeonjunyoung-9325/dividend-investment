"""인증정보를 노출하지 않는 공통 KIS GET 클라이언트."""

from collections.abc import Mapping
from enum import StrEnum, unique
from typing import ClassVar, Final, Protocol, final

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError

from src.kis.exceptions import (
    KisApiRateLimitError,
    KisApiResponseError,
    KisAuthenticationError,
    KisNetworkError,
    KisReadOnlyViolationError,
    KisResponseValidationError,
)
from src.kis.rate_limiter import IntervalRateLimiter, RateLimiter
from src.kis.transport import HttpRequest, HttpResponse, HttpTransport, RequestsTransport

REAL_BASE_URL: Final = "https://openapi.koreainvestment.com:9443"
DEMO_BASE_URL: Final = "https://openapivts.koreainvestment.com:29443"
GATEWAY_RATE_LIMIT_CODES: Final = frozenset({"EGW00201", "EGW00215"})
AUTHENTICATION_CODES: Final = frozenset({"EGW00121", "EGW00122", "EGW00123"})
READ_ONLY_PATHS: Final = frozenset(
    {
        "/uapi/domestic-stock/v1/ksdinfo/dividend",
        "/uapi/domestic-stock/v1/trading/inquire-balance",
        "/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
        "/uapi/domestic-stock/v1/trading/period-rights",
        "/uapi/overseas-price/v1/quotations/period-rights",
        "/uapi/overseas-stock/v1/trading/inquire-balance",
        "/uapi/overseas-stock/v1/trading/inquire-period-trans",
        "/uapi/overseas-stock/v1/trading/inquire-present-balance",
    }
)
HTTP_UNAUTHORIZED: Final = frozenset({401, 403})
HTTP_RATE_LIMITED: Final = 429
HTTP_SUCCESS_MIN: Final = 200
HTTP_SUCCESS_MAX: Final = 300


@unique
class KisEnvironment(StrEnum):
    """한국투자증권 실전·모의 환경 구분."""

    REAL = "real"
    DEMO = "demo"


class KisClientConfig(BaseModel):
    """민감정보를 SecretStr로 보존하는 클라이언트 설정."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    environment: KisEnvironment
    app_key: SecretStr
    app_secret: SecretStr
    timeout_seconds: float = 10.0


class TokenProvider(Protocol):
    """영속 캐시 정책과 클라이언트를 분리하는 토큰 공급 계약."""

    def get_access_token(self) -> str:
        """현재 유효한 접근토큰을 반환합니다."""
        ...


class KisEnvelope(BaseModel):
    """모든 REST 조회 응답에 공통인 성공·오류 필드."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    rt_cd: str
    msg_cd: str
    msg1: str


class KisResponse(BaseModel):
    """검증을 통과한 응답 원문과 연속조회 헤더."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    body: bytes
    tr_cont: str


@final
class KisClient:
    """조회 전용 REST 호출과 공통 응답 검증을 수행합니다."""

    def __init__(
        self,
        config: KisClientConfig,
        token_provider: TokenProvider,
        transport: HttpTransport | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """주입된 토큰·전송·호출제한 구현으로 클라이언트를 구성합니다."""
        self._config = config
        self._token_provider = token_provider
        self._transport = transport or RequestsTransport()
        self._rate_limiter = rate_limiter or IntervalRateLimiter()

    @property
    def environment(self) -> KisEnvironment:
        """현재 실전·모의 환경을 반환합니다."""
        return self._config.environment

    def get(
        self,
        *,
        path: str,
        tr_id: str,
        params: Mapping[str, str],
        tr_cont: str = "",
    ) -> KisResponse:
        """공식 GET endpoint를 호출하고 공통 KIS 오류를 검증합니다."""
        if path not in READ_ONLY_PATHS:
            raise KisReadOnlyViolationError(path=path)
        self._rate_limiter.wait()
        request = HttpRequest(
            url=f"{self._base_url()}{path}",
            path=path,
            headers={
                "accept": "text/plain",
                "authorization": f"Bearer {self._token_provider.get_access_token()}",
                "appkey": self._config.app_key.get_secret_value(),
                "appsecret": self._config.app_secret.get_secret_value(),
                "custtype": "P",
                "tr_id": tr_id,
                "tr_cont": tr_cont,
            },
            params=dict(params),
            timeout_seconds=self._config.timeout_seconds,
        )
        response = self._send_with_single_retry(request)
        self._check_http_status(response)
        try:
            envelope = KisEnvelope.model_validate_json(response.body)
        except ValidationError as error:
            raise KisResponseValidationError(endpoint=path) from error
        if envelope.rt_cd != "0":
            if envelope.msg_cd in GATEWAY_RATE_LIMIT_CODES:
                raise KisApiRateLimitError(code=envelope.msg_cd)
            if envelope.msg_cd in AUTHENTICATION_CODES:
                raise KisAuthenticationError(status_code=response.status_code, code=envelope.msg_cd)
            raise KisApiResponseError(code=envelope.msg_cd, message=envelope.msg1)
        return KisResponse(body=response.body, tr_cont=response.headers.get("tr_cont", ""))

    def _base_url(self) -> str:
        return REAL_BASE_URL if self._config.environment is KisEnvironment.REAL else DEMO_BASE_URL

    @staticmethod
    def _check_http_status(response: HttpResponse) -> None:
        if response.status_code in HTTP_UNAUTHORIZED:
            raise KisAuthenticationError(status_code=response.status_code)
        if response.status_code == HTTP_RATE_LIMITED:
            raise KisApiRateLimitError(code="HTTP_429")
        if response.status_code < HTTP_SUCCESS_MIN or response.status_code >= HTTP_SUCCESS_MAX:
            raise KisApiResponseError(code=f"HTTP_{response.status_code}", message="request failed")

    def _send_with_single_retry(self, request: HttpRequest) -> HttpResponse:
        try:
            return self._transport.send(request)
        except KisNetworkError:
            return self._transport.send(request)
