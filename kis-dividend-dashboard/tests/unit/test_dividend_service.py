from datetime import UTC, date, datetime
from decimal import Decimal

from src.kis.dividends import OverseasRightApi
from src.services.dividend_service import normalize_overseas_rights


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
