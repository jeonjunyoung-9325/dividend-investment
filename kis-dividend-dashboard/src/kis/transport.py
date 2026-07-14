"""비밀정보 로깅 없이 HTTP 요청을 전달하는 전송 경계."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

import requests

from src.kis.exceptions import KisNetworkError


@dataclass(frozen=True, slots=True)
class HttpRequest:
    """전송 구현에 전달되는 완전한 GET 요청."""

    url: str
    path: str
    headers: Mapping[str, str]
    params: Mapping[str, str]
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """외부 응답을 bytes로 보존하는 전송 결과."""

    status_code: int
    headers: Mapping[str, str]
    body: bytes


class HttpTransport(Protocol):
    """실제 HTTP와 테스트 더블이 공유하는 전송 계약."""

    def send(self, request: HttpRequest) -> HttpResponse:
        """단일 HTTP 요청을 전달합니다."""
        ...


class RequestsTransport:
    """프로젝트 표준 requests 기반 동기 전송 구현."""

    def send(self, request: HttpRequest) -> HttpResponse:
        """timeout과 연결 실패만 구조화해 GET 요청을 보냅니다."""
        try:
            response = requests.get(
                request.url,
                headers=request.headers,
                params=request.params,
                timeout=request.timeout_seconds,
            )
        except requests.Timeout as error:
            raise KisNetworkError(reason="timeout") from error
        except requests.ConnectionError as error:
            raise KisNetworkError(reason="connection failed") from error
        return HttpResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.content,
        )
