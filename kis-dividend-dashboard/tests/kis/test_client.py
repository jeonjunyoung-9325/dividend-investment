from collections import deque

import pytest
from pydantic import SecretStr
from src.kis.client import KisClient, KisClientConfig, KisEnvironment
from src.kis.exceptions import (
    KisApiRateLimitError,
    KisApiResponseError,
    KisAuthenticationError,
    KisNetworkError,
    KisReadOnlyViolationError,
)
from src.kis.transport import HttpRequest, HttpResponse, HttpTransport

from tests.kis.fakes import FakeTransport, StaticTokenProvider


def make_client(transport: HttpTransport) -> KisClient:
    credential = SecretStr("opaque-test-value")
    return KisClient(
        config=KisClientConfig(
            environment=KisEnvironment.REAL,
            app_key=credential,
            app_secret=credential,
        ),
        token_provider=StaticTokenProvider(),
        transport=transport,
    )


def test_get_raises_structured_error_for_failed_kis_response() -> None:
    # Given
    transport = FakeTransport(
        deque(
            [
                HttpResponse(
                    status_code=200,
                    headers={},
                    body=b'{"rt_cd":"1","msg_cd":"X001","msg1":"failed"}',
                )
            ]
        )
    )

    # When / Then
    with pytest.raises(KisApiResponseError, match="X001"):
        _ = make_client(transport).get(
            path="/uapi/domestic-stock/v1/trading/inquire-balance",
            tr_id="TR001",
            params={},
        )


def test_get_maps_confirmed_gateway_limit_code_without_retry() -> None:
    # Given
    transport = FakeTransport(
        deque(
            [
                HttpResponse(
                    status_code=200,
                    headers={},
                    body=b'{"rt_cd":"1","msg_cd":"EGW00201","msg1":"limit"}',
                )
            ]
        )
    )

    # When / Then
    with pytest.raises(KisApiRateLimitError):
        _ = make_client(transport).get(
            path="/uapi/domestic-stock/v1/trading/inquire-balance",
            tr_id="TR001",
            params={},
        )
    assert len(transport.requests) == 1


def test_get_supplies_required_headers_without_exposing_them_in_result() -> None:
    # Given
    transport = FakeTransport(
        deque(
            [
                HttpResponse(
                    status_code=200,
                    headers={"tr_cont": ""},
                    body=b'{"rt_cd":"0","msg_cd":"","msg1":"ok"}',
                )
            ]
        )
    )

    # When
    response = make_client(transport).get(
        path="/uapi/domestic-stock/v1/trading/inquire-balance",
        tr_id="TR001",
        params={"A": "1"},
    )

    # Then
    request = transport.requests[0]
    assert request.headers["authorization"] == "Bearer opaque-test-value"
    assert request.headers["tr_id"] == "TR001"
    assert response.tr_cont == ""


def test_order_path_is_blocked_before_transport() -> None:
    # Given
    transport = FakeTransport(deque())

    # When / Then
    with pytest.raises(KisReadOnlyViolationError):
        _ = make_client(transport).get(
            path="/uapi/domestic-stock/v1/trading/order-cash",
            tr_id="TTTC0802U",
            params={},
        )
    assert transport.requests == []


@pytest.mark.parametrize("code", ["EGW00121", "EGW00122", "EGW00123"])
def test_confirmed_authentication_codes_are_not_retried(code: str) -> None:
    # Given
    body = f'{{"rt_cd":"1","msg_cd":"{code}","msg1":"auth"}}'.encode()
    transport = FakeTransport(deque([HttpResponse(200, {}, body)]))

    # When / Then
    with pytest.raises(KisAuthenticationError):
        _ = make_client(transport).get(
            path="/uapi/domestic-stock/v1/trading/inquire-balance",
            tr_id="TR001",
            params={},
        )
    assert len(transport.requests) == 1


def test_confirmed_rate_limit_code_is_not_retried() -> None:
    # Given
    body = b'{"rt_cd":"1","msg_cd":"EGW00215","msg1":"limit"}'
    transport = FakeTransport(deque([HttpResponse(200, {}, body)]))

    # When / Then
    with pytest.raises(KisApiRateLimitError):
        _ = make_client(transport).get(
            path="/uapi/domestic-stock/v1/trading/inquire-balance",
            tr_id="TR001",
            params={},
        )
    assert len(transport.requests) == 1


class RetryOnceTransport:
    def __init__(self, *, always_fail: bool = False) -> None:
        self.always_fail: bool = always_fail
        self.attempts: int = 0

    def send(self, request: HttpRequest) -> HttpResponse:
        _ = request
        self.attempts += 1
        if self.always_fail or self.attempts == 1:
            raise KisNetworkError(reason="temporary")
        return HttpResponse(200, {}, b'{"rt_cd":"0","msg_cd":"","msg1":"ok"}')


def test_network_error_is_retried_once() -> None:
    # Given
    transport = RetryOnceTransport()

    # When
    _ = make_client(transport).get(
        path="/uapi/domestic-stock/v1/trading/inquire-balance",
        tr_id="TR001",
        params={},
    )

    # Then
    assert transport.attempts == 2


def test_second_network_error_stops_retrying() -> None:
    # Given
    transport = RetryOnceTransport(always_fail=True)

    # When / Then
    with pytest.raises(KisNetworkError):
        _ = make_client(transport).get(
            path="/uapi/domestic-stock/v1/trading/inquire-balance",
            tr_id="TR001",
            params={},
        )
    assert transport.attempts == 2
