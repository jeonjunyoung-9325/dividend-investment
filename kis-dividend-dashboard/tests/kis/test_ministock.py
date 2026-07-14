import json
from collections import deque
from decimal import Decimal

from pydantic import SecretStr
from src.kis.client import KisClient, KisClientConfig, KisEnvironment
from src.kis.ministock import MiniStockBalanceRequest, fetch_ministock_balance
from src.kis.transport import HttpResponse

from tests.kis.fakes import FakeTransport, StaticTokenProvider


def _client(transport: FakeTransport) -> KisClient:
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


def _body(symbol: str) -> bytes:
    return json.dumps(
        {
            "rt_cd": "0",
            "msg_cd": "KIOK0530",
            "msg1": "ok",
            "output1": [
                {
                    "pdno": symbol,
                    "prdt_name": "Schwab US Dividend Equity ETF",
                    "cblc_qty13": "28.062709",
                    "ord_psbl_qty1": "28.062709",
                    "avg_unpr3": "27.43",
                    "ovrs_now_pric1": "28.11",
                    "frcr_pchs_amt": "769.82",
                    "frcr_evlu_amt2": "788.91",
                    "evlu_pfls_amt2": "19.09",
                    "evlu_pfls_rt1": "2.4798",
                    "bass_exrt": "1504.90",
                    "buy_crcy_cd": "USD",
                    "ovrs_excg_cd": "AMEX",
                }
            ],
        }
    ).encode()


def test_ministock_balance_uses_fractional_holdings_query_and_continuation() -> None:
    # Given
    transport = FakeTransport(
        deque(
            [
                HttpResponse(200, {"tr_cont": "M"}, _body("SCHD")),
                HttpResponse(200, {"tr_cont": "E"}, _body("VOO")),
            ]
        )
    )

    # When
    result = fetch_ministock_balance(
        _client(transport), MiniStockBalanceRequest(account_no="12345678")
    )

    # Then
    assert [position.symbol for position in result.positions] == ["SCHD", "VOO"]
    assert result.positions[0].quantity == Decimal("28.062709")
    assert result.positions[0].exchange_rate == Decimal("1504.90")
    assert transport.requests[0].path.endswith("/inquire-present-balance")
    assert transport.requests[0].headers["tr_id"] == "CTRP6504R"
    assert transport.requests[0].params["INQR_DVSN_CD"] == "02"
    assert transport.requests[0].params["NATN_CD"] == "000"
    assert transport.requests[1].headers["tr_cont"] == "N"
