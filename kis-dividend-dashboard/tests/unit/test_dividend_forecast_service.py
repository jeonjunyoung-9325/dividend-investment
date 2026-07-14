from datetime import UTC, date, datetime
from decimal import Decimal

from src.calculations.dividend_forecast import ForecastMethod
from src.models import DividendEvent, DividendPayment, PortfolioSnapshot
from src.services.dividend_forecast_service import ForecastEvidence, ForecastTaxRates, forecast_rows


def _position() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        sync_run_id="run",
        snapshot_at=datetime(2026, 7, 15, tzinfo=UTC),
        market="overseas",
        exchange="NASD",
        symbol="JEPI",
        name="JPMorgan Equity Premium Income ETF",
        quantity=Decimal("10.5"),
        currency="USD",
        krw_exchange_rate=Decimal(1380),
        source="test",
    )


def _event(month: int, amount: str) -> DividendEvent:
    event_date = date(2026, month, 5)
    return DividendEvent(
        event_key=f"event-{month}",
        market="overseas",
        exchange="NASD",
        symbol="JEPI",
        record_date=event_date,
        amount_per_share=Decimal(amount),
        currency="USD",
        status="confirmed",
        source="KIS overseas dividend rights",
        fetched_at=datetime(2026, 7, 15, tzinfo=UTC),
    )


def test_forecast_uses_official_event_history_and_converts_to_krw() -> None:
    # Given: six past official per-share events and a fractional overseas holding.
    events = tuple(
        _event(month, amount)
        for month, amount in enumerate(("0.35", "0.36", "0.34", "0.37", "0.33", "0.35"), start=1)
    )

    # When: the twelve-month forecast is built without imported payments.
    rows = forecast_rows(
        (_position(),),
        ForecastEvidence((), events),
        as_of=date(2026, 7, 15),
        tax_rates=ForecastTaxRates(Decimal("0.154"), Decimal("0.15"), Decimal("0.20")),
    )

    # Then: official events drive the estimate and native amounts are converted exactly.
    row = rows[0]
    assert row["예상 세전"] == Decimal("44.10")
    assert row["예상 세후"] == Decimal("37.4850")
    assert row["예상 세전 원화"] == Decimal("60858.00")
    assert row["예상 세후 원화"] == Decimal("51729.3000")
    assert row["출처"] == "KIS overseas dividend rights"


def test_actual_payment_history_wins_over_duplicate_event() -> None:
    # Given: the same asset/date/amount exists as an actual payment and an official event.
    event = _event(6, "0.35")
    payment = DividendPayment(
        market="overseas",
        exchange="NASD",
        symbol="JEPI",
        name="JEPI",
        payment_date=date(2026, 6, 5),
        gross_amount=Decimal("3.675"),
        tax_amount=Decimal("0.55125"),
        net_amount=Decimal("3.12375"),
        amount_per_share=Decimal("0.35"),
        currency="USD",
        source="user_upload",
    )

    # When: a one-observation method is selected explicitly.
    rows = forecast_rows(
        (_position(),),
        ForecastEvidence((payment,), (event,)),
        as_of=date(2026, 7, 15),
        tax_rates=ForecastTaxRates(Decimal("0.154"), Decimal("0.15"), Decimal("0.20")),
        symbol_overrides={"JEPI": (None, ForecastMethod.LAST_ONE, None)},
    )

    # Then: the sample is not double-counted and the actual source remains visible.
    assert rows[0]["표본 수"] == 1
    assert rows[0]["출처"] == "user_upload"
