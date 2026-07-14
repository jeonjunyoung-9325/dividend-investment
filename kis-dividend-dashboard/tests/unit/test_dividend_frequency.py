from datetime import date

import pytest
from src.calculations.dividend_frequency import DividendFrequency, infer_frequency


@pytest.mark.parametrize(
    ("payment_dates", "expected"),
    [
        ([date(2026, month, 15) for month in range(1, 7)], DividendFrequency.MONTHLY),
        (
            [date(2025, 7, 15), date(2025, 10, 15), date(2026, 1, 15), date(2026, 4, 15)],
            DividendFrequency.QUARTERLY,
        ),
        (
            [date(2024, 7, 15), date(2025, 1, 15), date(2025, 7, 15), date(2026, 1, 15)],
            DividendFrequency.SEMIANNUAL,
        ),
        (
            [date(2023, 4, 15), date(2024, 4, 15), date(2025, 4, 15), date(2026, 4, 15)],
            DividendFrequency.ANNUAL,
        ),
        (
            [date(2025, 1, 1), date(2025, 2, 1), date(2025, 8, 1), date(2026, 1, 1)],
            DividendFrequency.IRREGULAR,
        ),
        ([date(2026, 1, 15), date(2026, 4, 15)], DividendFrequency.UNKNOWN),
    ],
)
def test_frequency_when_payment_intervals_are_observed(
    payment_dates: list[date], expected: DividendFrequency
) -> None:
    # Given: only actual payment dates, with no symbol-name hints.
    # When: interval statistics are evaluated.
    result = infer_frequency(payment_dates)

    # Then: classification follows timing and data sufficiency.
    assert result.frequency == expected


def test_frequency_is_order_independent_and_deduplicates_dates() -> None:
    # Given: quarterly dates in reverse order with a duplicate.
    dates = [
        date(2026, 4, 15),
        date(2026, 1, 15),
        date(2025, 10, 15),
        date(2025, 7, 15),
        date(2026, 1, 15),
    ]

    # When: frequency is detected.
    result = infer_frequency(dates)

    # Then: duplicates do not inflate the sample count.
    assert result.frequency is DividendFrequency.QUARTERLY
    assert result.sample_count == 4
