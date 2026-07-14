from datetime import UTC, date, datetime
from decimal import Decimal

from src.kis.dividends import DomesticAccountRightApi, OverseasRightApi
from src.models import DividendEvent
from src.services.dividend_service import (
    normalize_overseas_rights,
    normalize_verified_domestic_payments,
)


def test_overseas_rights_normalization_uses_exact_symbol_and_cash_amount() -> None:
    # Given: the KIS prefix search returns both the held ticker and a similarly named ticker.
    rights = (
        _right("QQQ", "0.67686"),
        _right("QQQM", "0.29987"),
    )

    # When: the response is normalized for the held QQQ position.
    events = normalize_overseas_rights(
        rights,
        exchange="NASD",
        symbol="QQQ",
        fetched_at=datetime(2026, 7, 15, tzinfo=UTC),
    )

    # Then: only the exact symbol is retained with the official local record date.
    assert len(events) == 1
    assert events[0].symbol == "QQQ"
    assert events[0].record_date == date(2026, 6, 23)
    assert events[0].payment_date is None
    assert events[0].amount_per_share == Decimal("0.67686")
    assert events[0].status == "confirmed"


def _right(symbol: str, amount: str) -> OverseasRightApi:
    return OverseasRightApi(
        acpl_bass_dt="20260623",
        rght_type_cd="03",
        pdno=symbol,
        prdt_name=symbol,
        crcy_cd="USD",
        alct_frcr_unpr=Decimal(amount),
        dfnt_yn="Y",
    )


def test_domestic_cash_right_becomes_actual_only_when_schedule_reconciles() -> None:
    # Given: account cash data exactly reconciles with the official per-share schedule.
    right = DomesticAccountRightApi(
        rght_type_cd="32",
        rght_cblc_type_cd="01",
        bass_dt="20260630",
        pdno="00000A475720",
        shtn_pdno="475720",
        prdt_name="RISE 200위클리커버드콜",
        cblc_qty=Decimal(20),
        last_alct_amt=Decimal(5600),
        cash_dfrm_dt="20260702",
        tax_amt=Decimal(0),
    )
    event = DividendEvent(
        event_key="event",
        market="domestic",
        exchange="KRX",
        symbol="475720",
        record_date=date(2026, 6, 30),
        payment_date=date(2026, 7, 2),
        amount_per_share=Decimal(280),
        currency="KRW",
        status="announced_unverified",
        source="KIS domestic dividend schedule",
        fetched_at=datetime(2026, 7, 15, tzinfo=UTC),
    )

    # When: actual payments are normalized at the two-source reconciliation boundary.
    payments = normalize_verified_domestic_payments((right,), (event,), as_of=date(2026, 7, 15))

    # Then: exact actual gross, tax, net, quantity, and per-share values are retained.
    assert len(payments) == 1
    assert payments[0].gross_amount == Decimal(5600)
    assert payments[0].tax_amount == Decimal(0)
    assert payments[0].net_amount == Decimal(5600)
    assert payments[0].amount_per_share == Decimal(280)
    assert payments[0].source == "KIS 계좌 권리·배당일정 대조"


def test_ambiguous_taxed_account_right_is_not_imported_as_actual() -> None:
    # Given: a taxed account-right amount whose gross/net meaning is not documented.
    right = DomesticAccountRightApi(
        rght_type_cd="03",
        bass_dt="20260630",
        pdno="005930",
        prdt_name="삼성전자",
        cblc_qty=Decimal(10),
        last_alct_amt=Decimal(3650),
        cash_dfrm_dt="20260702",
        tax_amt=Decimal(550),
    )

    # When: it reaches the actual-payment normalization boundary.
    payments = normalize_verified_domestic_payments((right,), (), as_of=date(2026, 7, 15))

    # Then: no gross/net values are guessed.
    assert payments == ()
