"""Twelve-month per-share dividend forecast strategies."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum
from statistics import median

from src.calculations.dividend_frequency import DividendFrequency, FrequencyResult, infer_frequency
from src.schemas import DividendHistoryItem

HIGH_CONFIDENCE_SAMPLE_COUNT = 4
IRREGULAR_MINIMUM_SPAN_DAYS = 183


class ForecastMethod(StrEnum):
    """User-selectable forecast strategies."""

    LAST_12_MONTHS = "last_12_months"
    SIX_MONTH_MEDIAN = "six_month_median"
    THREE_MONTH_AVERAGE = "three_month_average"
    LAST_FOUR = "last_four"
    LAST_TWO = "last_two"
    LAST_ONE = "last_one"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class DividendForecast:
    """Forecast result with method and sufficiency evidence."""

    annual_per_share: Decimal | None
    gross_amount: Decimal | None
    method: ForecastMethod | None
    frequency: DividendFrequency
    annual_payments: int | None
    sample_count: int
    data_start: date | None
    data_end: date | None
    confidence: str
    sufficient: bool
    source: str


def default_method(frequency: DividendFrequency) -> ForecastMethod | None:
    """Choose the conservative method defined by the product specification."""
    mapping = {
        DividendFrequency.MONTHLY: ForecastMethod.SIX_MONTH_MEDIAN,
        DividendFrequency.QUARTERLY: ForecastMethod.LAST_FOUR,
        DividendFrequency.SEMIANNUAL: ForecastMethod.LAST_TWO,
        DividendFrequency.ANNUAL: ForecastMethod.LAST_ONE,
    }
    return mapping.get(frequency)


def forecast_dividend(
    history: list[DividendHistoryItem],
    current_quantity: Decimal,
    as_of: date,
    method: ForecastMethod | None = None,
    manual_annual_per_share: Decimal | None = None,
) -> DividendForecast:
    """Forecast annual dividends while refusing unsupported extrapolation."""
    ordered = sorted(
        (item for item in history if item.payment_date <= as_of),
        key=lambda item: item.payment_date,
    )
    frequency_result = infer_frequency([item.payment_date for item in ordered])
    chosen = method or default_method(frequency_result.frequency) or _irregular_method(ordered)
    if chosen is ForecastMethod.MANUAL:
        if manual_annual_per_share is None or manual_annual_per_share < 0:
            return _unavailable(frequency_result, chosen, ordered, "user")
        return _available(
            manual_annual_per_share, current_quantity, chosen, frequency_result, ordered, "user"
        )
    if chosen is None:
        return _unavailable(frequency_result, None, ordered, "calculated")
    samples = _samples_for_method(ordered, chosen, as_of)
    required = {
        ForecastMethod.LAST_12_MONTHS: 1,
        ForecastMethod.SIX_MONTH_MEDIAN: 3,
        ForecastMethod.THREE_MONTH_AVERAGE: 2,
        ForecastMethod.LAST_FOUR: 4,
        ForecastMethod.LAST_TWO: 2,
        ForecastMethod.LAST_ONE: 1,
    }[chosen]
    if len(samples) < required:
        return _unavailable(frequency_result, chosen, samples, "calculated")
    amounts = [item.amount_per_share for item in samples]
    annual_payments = frequency_result.annual_payments
    if chosen is ForecastMethod.SIX_MONTH_MEDIAN:
        annual = Decimal(str(median(amounts))) * Decimal(annual_payments or 12)
    elif chosen is ForecastMethod.THREE_MONTH_AVERAGE:
        annual = sum(amounts, Decimal(0)) / Decimal(len(amounts)) * Decimal(annual_payments or 12)
    else:
        annual = sum(amounts, Decimal(0))
    return _available(annual, current_quantity, chosen, frequency_result, samples, "calculated")


def _irregular_method(history: list[DividendHistoryItem]) -> ForecastMethod | None:
    if len(history) < HIGH_CONFIDENCE_SAMPLE_COUNT:
        return None
    span = (history[-1].payment_date - history[0].payment_date).days
    return ForecastMethod.LAST_12_MONTHS if span >= IRREGULAR_MINIMUM_SPAN_DAYS else None


def _samples_for_method(
    history: list[DividendHistoryItem], method: ForecastMethod, as_of: date
) -> list[DividendHistoryItem]:
    if method is ForecastMethod.LAST_12_MONTHS:
        cutoff = as_of - timedelta(days=365)
        return [item for item in history if cutoff <= item.payment_date <= as_of]
    if method is ForecastMethod.SIX_MONTH_MEDIAN:
        cutoff = as_of - timedelta(days=183)
        return [item for item in history if cutoff <= item.payment_date <= as_of]
    if method is ForecastMethod.THREE_MONTH_AVERAGE:
        cutoff = as_of - timedelta(days=92)
        return [item for item in history if cutoff <= item.payment_date <= as_of]
    counts = {ForecastMethod.LAST_FOUR: 4, ForecastMethod.LAST_TWO: 2, ForecastMethod.LAST_ONE: 1}
    return history[-counts[method] :]


def _available(
    annual: Decimal,
    quantity: Decimal,
    method: ForecastMethod,
    frequency: FrequencyResult,
    samples: list[DividendHistoryItem],
    source: str,
) -> DividendForecast:
    return DividendForecast(
        annual_per_share=annual,
        gross_amount=annual * quantity,
        method=method,
        frequency=frequency.frequency,
        annual_payments=frequency.annual_payments,
        sample_count=len(samples),
        data_start=samples[0].payment_date if samples else None,
        data_end=samples[-1].payment_date if samples else None,
        confidence="high" if len(samples) >= HIGH_CONFIDENCE_SAMPLE_COUNT else "medium",
        sufficient=True,
        source=source,
    )


def _unavailable(
    frequency: FrequencyResult,
    method: ForecastMethod | None,
    samples: list[DividendHistoryItem],
    source: str,
) -> DividendForecast:
    return DividendForecast(
        annual_per_share=None,
        gross_amount=None,
        method=method,
        frequency=frequency.frequency,
        annual_payments=frequency.annual_payments,
        sample_count=len(samples),
        data_start=samples[0].payment_date if samples else None,
        data_end=samples[-1].payment_date if samples else None,
        confidence="insufficient",
        sufficient=False,
        source=source,
    )
