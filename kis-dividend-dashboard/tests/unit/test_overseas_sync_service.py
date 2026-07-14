import json
from collections import deque
from datetime import UTC, datetime
from decimal import Decimal

from pydantic import SecretStr
from src.kis.client import KisClient, KisClientConfig, KisEnvironment
from src.kis.transport import HttpResponse
from src.services.overseas_sync_service import OverseasSyncRequest, fetch_overseas_positions

from tests.kis.fakes import FakeTransport, StaticTokenProvider


def test_overseas_sync_includes_general_and_ministock_positions() -> None:
    # Given
    transport = FakeTransport(
        deque(
            [
                HttpResponse(200, {}, _general_balance()),
                HttpResponse(200, {}, _ministock_balance()),
            ]
        )
    )
    credential = SecretStr("opaque-test-value")
    client = KisClient(
        KisClientConfig(
            environment=KisEnvironment.REAL,
            app_key=credential,
            app_secret=credential,
        ),
        StaticTokenProvider(),
        transport=transport,
    )

    # When
    status, positions, failures = fetch_overseas_positions(
        client,
        OverseasSyncRequest(
            account="12345678",
            product_code="01",
            exchanges=("NASD",),
            rates={"USD": Decimal(1500)},
            now=datetime(2026, 7, 15, tzinfo=UTC),
        ),
    )

    # Then
    assert status == "success"
    assert failures == []
    assert {position.symbol for position in positions} == {"NVDY", "SCHD"}
    assert transport.requests[1].params["INQR_DVSN_CD"] == "02"


def test_ministock_failure_keeps_general_overseas_positions() -> None:
    # Given
    failed_ministock = json.dumps(
        {"rt_cd": "1", "msg_cd": "TEST_FAILURE", "msg1": "temporary failure"}
    ).encode()
    transport = FakeTransport(
        deque(
            [
                HttpResponse(200, {}, _general_balance()),
                HttpResponse(200, {}, failed_ministock),
            ]
        )
    )
    credential = SecretStr("opaque-test-value")
    client = KisClient(
        KisClientConfig(
            environment=KisEnvironment.REAL,
            app_key=credential,
            app_secret=credential,
        ),
        StaticTokenProvider(),
        transport=transport,
    )

    # When
    status, positions, failures = fetch_overseas_positions(
        client,
        OverseasSyncRequest(
            account="12345678",
            product_code="01",
            exchanges=("NASD",),
            rates={"USD": Decimal(1500)},
            now=datetime(2026, 7, 15, tzinfo=UTC),
        ),
    )

    # Then
    assert status == "partial"
    assert [position.symbol for position in positions] == ["NVDY"]
    assert failures == ["미니스탁 잔고 조회 실패"]


def _general_balance() -> bytes:
    return json.dumps(
        {
            "rt_cd": "0",
            "msg_cd": "",
            "msg1": "ok",
            "ctx_area_fk200": "",
            "ctx_area_nk200": "",
            "output1": [
                {
                    "ovrs_pdno": "NVDY",
                    "ovrs_item_name": "YieldMax NVDA",
                    "ovrs_cblc_qty": "2",
                    "ord_psbl_qty": "2",
                    "pchs_avg_pric": "20",
                    "frcr_pchs_amt1": "40",
                    "now_pric2": "21",
                    "ovrs_stck_evlu_amt": "42",
                    "frcr_evlu_pfls_amt": "2",
                    "evlu_pfls_rt": "5",
                    "tr_crcy_cd": "USD",
                    "ovrs_excg_cd": "NASD",
                }
            ],
        }
    ).encode()


def _ministock_balance() -> bytes:
    return json.dumps(
        {
            "rt_cd": "0",
            "msg_cd": "",
            "msg1": "ok",
            "output1": [
                {
                    "pdno": "SCHD",
                    "prdt_name": "Schwab ETF",
                    "cblc_qty13": "0.5",
                    "ord_psbl_qty1": "0.5",
                    "avg_unpr3": "70",
                    "ovrs_now_pric1": "75",
                    "frcr_pchs_amt": "35",
                    "frcr_evlu_amt2": "37.5",
                    "evlu_pfls_amt2": "2.5",
                    "evlu_pfls_rt1": "7.142857",
                    "bass_exrt": "1500",
                    "buy_crcy_cd": "USD",
                    "ovrs_excg_cd": "AMEX",
                }
            ],
        }
    ).encode()
