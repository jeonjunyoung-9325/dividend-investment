from datetime import date
from decimal import Decimal

import pytest
from src.calculations.dividend_forecast import ForecastMethod, forecast_dividend
from src.schemas import DividendHistoryItem

PAYMENTS = [
    DividendHistoryItem(
        payment_date=date(2026, month, 15),
        amount_per_share=Decimal(f"0.{month}"),
        currency="USD",
        source="fixture",
    )
    for month in range(1, 7)
]


@pytest.mark.parametrize(
    ("method", "expected"),
    [
        (ForecastMethod.LAST_12_MONTHS, Decimal("2.1")),
        (ForecastMethod.SIX_MONTH_MEDIAN, Decimal("4.2")),
        (ForecastMethod.THREE_MONTH_AVERAGE, Decimal("6.0")),
        (ForecastMethod.LAST_FOUR, Decimal("1.8")),
        (ForecastMethod.LAST_TWO, Decimal("1.1")),
        (ForecastMethod.LAST_ONE, Decimal("0.6")),
    ],
)
def test_annual_per_share_when_supported_method_is_selected(
    method: ForecastMethod,
    expected: Decimal,
) -> None:
    # Given: six dated, per-share dividend payments with exact Decimal values.
    # When: the requested forecast method is evaluated as of a fixed date.
    estimate = forecast_dividend(
        PAYMENTS,
        current_quantity=Decimal(10),
        method=method,
        as_of=date(2026, 7, 14),
    )

    # Then: the selected method alone determines the annual per-share amount.
    assert estimate.annual_per_share == expected


def test_manual_annual_per_share_when_user_override_exists() -> None:
    # Given: an override distinct from every history-based fallback.
    # When: the manual method is selected.
    estimate = forecast_dividend(
        PAYMENTS,
        current_quantity=Decimal(10),
        method=ForecastMethod.MANUAL,
        as_of=date(2026, 7, 14),
        manual_annual_per_share=Decimal("9.8765"),
    )

    # Then: the exact override is returned without float conversion.
    assert estimate.annual_per_share == Decimal("9.8765")


def test_unavailable_when_history_is_insufficient_for_selected_method() -> None:
    # Given: one observation for a four-payment method.
    # When: a recent-four forecast is requested.
    estimate = forecast_dividend(
        PAYMENTS[-1:],
        current_quantity=Decimal(10),
        method=ForecastMethod.LAST_FOUR,
        as_of=date(2026, 7, 14),
    )

    # Then: the result is explicitly unavailable rather than silently annualized.
    assert estimate.annual_per_share is None
    assert estimate.sufficient is False


def test_last_twelve_months_is_default_for_rich_irregular_history() -> None:
    # Given: a variable distribution series with enough observations across most of a year.
    history = [
        DividendHistoryItem(
            payment_date=payment_date,
            amount_per_share=Decimal("0.25"),
            currency="USD",
            source="official",
        )
        for payment_date in (
            date(2025, 8, 1),
            date(2025, 9, 15),
            date(2025, 11, 1),
            date(2026, 1, 16),
            date(2026, 3, 1),
            date(2026, 5, 22),
            date(2026, 7, 1),
        )
    ]

    # When: no user method override is supplied.
    estimate = forecast_dividend(history, Decimal(10), date(2026, 7, 15))

    # Then: the observed twelve-month total is used without inventing a cadence multiplier.
    assert estimate.method is ForecastMethod.LAST_12_MONTHS
    assert estimate.annual_per_share == Decimal("1.75")
    assert estimate.gross_amount == Decimal("17.50")
