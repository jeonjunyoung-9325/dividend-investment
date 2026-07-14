import json
from collections import deque
from decimal import Decimal

from pydantic import SecretStr
from src.kis.client import KisClient, KisClientConfig, KisEnvironment
from src.kis.dividends import (
    DomesticAccountRightsRequest,
    DomesticDividendScheduleRequest,
    OverseasRightsRequest,
    fetch_domestic_account_rights,
    fetch_domestic_dividend_schedule,
    fetch_overseas_rights,
)
from src.kis.transactions import (
    DomesticTransactionsRequest,
    OverseasTransactionsRequest,
    fetch_domestic_transactions,
    fetch_overseas_transactions,
)
from src.kis.transport import HttpResponse

from tests.kis.fakes import FakeTransport, StaticTokenProvider

type JsonValue = str | int | list[JsonValue] | dict[str, JsonValue] | None


def client(transport: FakeTransport) -> KisClient:
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


def payload(**values: JsonValue) -> bytes:
    return json.dumps(values, ensure_ascii=False).encode()


def test_overseas_transactions_parse_decimal_and_use_confirmed_tr() -> None:
    # Given
    transaction = {
        "trad_dt": "20260701",
        "sttl_dt": "20260703",
        "pdno": "SCHD",
        "ovrs_item_name": "Schwab ETF",
        "sll_buy_dvsn_cd": "02",
        "ccld_qty": "1",
        "ovrs_stck_ccld_unpr": "75.25",
        "tr_frcr_amt2": "75.25",
        "wcrc_excc_amt": "103000",
        "crcy_cd": "USD",
        "erlm_exrt": "1368.77",
    }
    body = payload(
        rt_cd="0",
        msg_cd="",
        msg1="ok",
        ctx_area_fk100="",
        ctx_area_nk100="",
        output1={},
        output2=[transaction],
    )
    transport = FakeTransport(deque([HttpResponse(200, {}, body)]))

    # When
    result = fetch_overseas_transactions(
        client(transport),
        OverseasTransactionsRequest(
            account_no="12345678",
            start_date="20260701",
            end_date="20260714",
            exchange="NASD",
        ),
    )

    # Then
    assert result[0].foreign_amount == Decimal("75.25")
    assert transport.requests[0].headers["tr_id"] == "CTOS4001R"
    assert transport.requests[0].path == "/uapi/overseas-stock/v1/trading/inquire-period-trans"


def test_domestic_transactions_use_confirmed_tr_and_cursor() -> None:
    # Given
    transaction = {
        "ord_dt": "20260701",
        "pdno": "005930",
        "prdt_name": "삼성전자",
        "sll_buy_dvsn_cd": "02",
        "tot_ccld_qty": "1",
        "avg_prvs": "75000",
        "tot_ccld_amt": "75000",
    }
    body = payload(
        rt_cd="0",
        msg_cd="",
        msg1="ok",
        ctx_area_fk100="",
        ctx_area_nk100="",
        output1=[transaction],
    )
    transport = FakeTransport(deque([HttpResponse(200, {}, body)]))

    # When
    result = fetch_domestic_transactions(
        client(transport),
        DomesticTransactionsRequest(
            account_no="12345678", start_date="20260701", end_date="20260714"
        ),
    )

    # Then
    assert result[0].tot_ccld_amt == Decimal(75000)
    assert transport.requests[0].headers["tr_id"] == "TTTC0081R"
    assert transport.requests[0].path == "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"


def test_domestic_dividend_schedule_is_market_data_not_payment_data() -> None:
    # Given
    schedule = {
        "record_date": "20260630",
        "sht_cd": "005930",
        "divi_kind": "중간",
        "per_sto_divi_amt": "365",
        "divi_pay_dt": "20260820",
    }
    body = payload(rt_cd="0", msg_cd="", msg1="ok", output1=[schedule])
    transport = FakeTransport(deque([HttpResponse(200, {}, body)]))

    # When
    result = fetch_domestic_dividend_schedule(
        client(transport),
        DomesticDividendScheduleRequest(start_date="20260101", end_date="20261231"),
    )

    # Then
    assert result[0].amount_per_share == Decimal(365)
    assert transport.requests[0].headers["tr_id"] == "HHKDB669102C0"
    assert transport.requests[0].path == "/uapi/domestic-stock/v1/ksdinfo/dividend"


def test_domestic_rights_use_confirmed_read_only_contract() -> None:
    # Given
    right = {
        "rght_type_cd": "03",
        "bass_dt": "20260630",
        "pdno": "005930",
        "prdt_name": "삼성전자",
        "cblc_qty": "10",
        "rght_cblc_type_cd": "10",
        "last_alct_amt": "3650",
        "cash_dfrm_dt": "20260820",
        "tax_amt": "550",
    }
    body = payload(
        rt_cd="0",
        msg_cd="",
        msg1="ok",
        ctx_area_fk100="",
        ctx_area_nk100="",
        output=[right],
    )
    transport = FakeTransport(deque([HttpResponse(200, {}, body)]))

    # When
    result = fetch_domestic_account_rights(
        client(transport),
        DomesticAccountRightsRequest(
            account_no="12345678", start_date="20260101", end_date="20261231"
        ),
    )

    # Then
    assert result[0].tax_amt == Decimal(550)
    assert result[0].last_alct_amt == Decimal(3650)
    assert result[0].rght_cblc_type_cd == "10"
    assert transport.requests[0].headers["tr_id"] == "CTRGA011R"
    assert transport.requests[0].path == "/uapi/domestic-stock/v1/trading/period-rights"


def test_overseas_rights_use_confirmed_read_only_contract() -> None:
    # Given
    right = {
        "acpl_bass_dt": "20260630",
        "rght_type_cd": "03",
        "pdno": "SCHD",
        "prdt_name": "Schwab ETF",
        "crcy_cd": "USD",
        "stkp_dvdn_frcr_amt2": "2.48",
        "dfnt_yn": "Y",
    }
    body = payload(
        rt_cd="0",
        msg_cd="",
        msg1="ok",
        ctx_area_fk50="",
        ctx_area_nk50="",
        output=[right],
    )
    transport = FakeTransport(deque([HttpResponse(200, {}, body)]))

    # When
    result = fetch_overseas_rights(
        client(transport), OverseasRightsRequest(start_date="20260101", end_date="20261231")
    )

    # Then
    assert result[0].stkp_dvdn_frcr_amt2 == Decimal("2.48")
    assert transport.requests[0].headers["tr_id"] == "CTRGT011R"
    assert transport.requests[0].path == "/uapi/overseas-price/v1/quotations/period-rights"
