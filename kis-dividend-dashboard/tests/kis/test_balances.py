import json
from collections import deque
from decimal import Decimal

from pydantic import SecretStr
from src.kis.client import KisClient, KisClientConfig, KisEnvironment
from src.kis.domestic import DomesticBalanceRequest, fetch_domestic_balance
from src.kis.overseas import OverseasBalanceRequest, OverseasExchange, fetch_overseas_balance
from src.kis.transport import HttpResponse

from tests.kis.fakes import FakeTransport, StaticTokenProvider

type JsonValue = str | int | list[JsonValue] | dict[str, JsonValue] | None


def client(
    transport: FakeTransport, environment: KisEnvironment = KisEnvironment.REAL
) -> KisClient:
    credential = SecretStr("opaque-test-value")
    return KisClient(
        config=KisClientConfig(
            environment=environment,
            app_key=credential,
            app_secret=credential,
        ),
        token_provider=StaticTokenProvider(),
        transport=transport,
    )


def payload(**values: JsonValue) -> bytes:
    return json.dumps(values).encode()


def domestic_holding(symbol: str) -> dict[str, str]:
    return {
        "pdno": symbol,
        "prdt_name": "Samsung",
        "hldg_qty": "1.25",
        "ord_psbl_qty": "1",
        "pchs_avg_pric": "70000",
        "pchs_amt": "87500",
        "prpr": "75000",
        "evlu_amt": "93750",
        "evlu_pfls_amt": "6250",
        "evlu_pfls_rt": "7.142857",
    }


def test_domestic_balance_uses_confirmed_tr_and_merges_pages() -> None:
    # Given
    first = payload(
        rt_cd="0",
        msg_cd="",
        msg1="ok",
        ctx_area_fk100="f2",
        ctx_area_nk100="n2",
        output1=[domestic_holding("005930")],
        output2=[{"dnca_tot_amt": "1000", "tot_evlu_amt": "94750", "nass_amt": "94750"}],
    )
    second = payload(
        rt_cd="0",
        msg_cd="",
        msg1="ok",
        ctx_area_fk100="",
        ctx_area_nk100="",
        output1=[domestic_holding("000660")],
        output2=[],
    )
    transport = FakeTransport(
        deque([HttpResponse(200, {"tr_cont": "M"}, first), HttpResponse(200, {}, second)])
    )

    # When
    result = fetch_domestic_balance(
        client(transport), DomesticBalanceRequest(account_no="12345678")
    )

    # Then
    assert [position.symbol for position in result.positions] == ["005930", "000660"]
    assert result.positions[0].quantity == Decimal("1.25")
    assert transport.requests[0].path == "/uapi/domestic-stock/v1/trading/inquire-balance"
    assert transport.requests[0].headers["tr_id"] == "TTTC8434R"
    assert transport.requests[1].params["CTX_AREA_FK100"] == "f2"
    assert transport.requests[1].headers["tr_cont"] == "N"


def test_overseas_balance_uses_exchange_and_currency_codes() -> None:
    # Given
    holding = {
        "ovrs_pdno": "SCHD",
        "ovrs_item_name": "Schwab ETF",
        "ovrs_cblc_qty": "3",
        "ord_psbl_qty": "3",
        "pchs_avg_pric": "70.10",
        "frcr_pchs_amt1": "210.30",
        "now_pric2": "75.20",
        "ovrs_stck_evlu_amt": "225.60",
        "frcr_evlu_pfls_amt": "15.30",
        "evlu_pfls_rt": "7.2753",
        "tr_crcy_cd": "USD",
        "ovrs_excg_cd": "NASD",
    }
    body = payload(
        rt_cd="0",
        msg_cd="",
        msg1="ok",
        ctx_area_fk200="",
        ctx_area_nk200="",
        output1=[holding],
    )
    transport = FakeTransport(deque([HttpResponse(200, {}, body)]))

    # When
    result = fetch_overseas_balance(
        client(transport),
        OverseasBalanceRequest(
            account_no="12345678", exchange=OverseasExchange.NASD, currency="USD"
        ),
    )

    # Then
    assert result.positions[0].symbol == "SCHD"
    assert result.positions[0].evaluation_amount == Decimal("225.60")
    assert transport.requests[0].headers["tr_id"] == "TTTS3012R"
    assert transport.requests[0].params["OVRS_EXCG_CD"] == "NASD"
