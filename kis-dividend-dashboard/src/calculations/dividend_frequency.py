"""Infer dividend frequency from observed payment intervals only."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from itertools import pairwise
from statistics import median, pstdev

MINIMUM_FREQUENCY_SAMPLES = 3


class DividendFrequency(StrEnum):
    """Supported date-derived payment cadence."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"
    IRREGULAR = "irregular"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FrequencyResult:
    """Frequency classification with observable evidence."""

    frequency: DividendFrequency
    sample_count: int
    median_interval_days: float | None
    dispersion_days: float | None
    annual_payments: int | None
    confidence: str


def infer_frequency(payment_dates: list[date]) -> FrequencyResult:
    """Classify payment cadence from unique sorted dates and interval dispersion."""
    dates = sorted(set(payment_dates))
    if len(dates) < MINIMUM_FREQUENCY_SAMPLES:
        return FrequencyResult(
            DividendFrequency.UNKNOWN, len(dates), None, None, None, "insufficient"
        )
    intervals = [(right - left).days for left, right in pairwise(dates)]
    middle = float(median(intervals))
    dispersion = float(pstdev(intervals)) if len(intervals) > 1 else 0.0
    if dispersion > max(18.0, middle * 0.22):
        return FrequencyResult(
            DividendFrequency.IRREGULAR, len(dates), middle, dispersion, None, "low"
        )
    bands = (
        (20, 45, DividendFrequency.MONTHLY, 12),
        (70, 115, DividendFrequency.QUARTERLY, 4),
        (150, 220, DividendFrequency.SEMIANNUAL, 2),
        (300, 430, DividendFrequency.ANNUAL, 1),
    )
    for low, high, frequency, annual_payments in bands:
        if low <= middle <= high:
            return FrequencyResult(
                frequency, len(dates), middle, dispersion, annual_payments, "high"
            )
    return FrequencyResult(DividendFrequency.IRREGULAR, len(dates), middle, dispersion, None, "low")
