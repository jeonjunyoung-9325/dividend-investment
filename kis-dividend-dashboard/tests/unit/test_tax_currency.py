from decimal import Decimal

import pytest
from src.calculations.currency import convert_to_krw
from src.calculations.tax import estimate_tax


def test_tax_estimate_when_market_rate_applies() -> None:
    # Given: a gross amount and the configured domestic assumption.
    # When: withholding and net are estimated.
    result = estimate_tax(Decimal("12345.67"), Decimal("0.154"))

    # Then: calculation is exact and unrounded at the domain boundary.
    assert result.withholding == Decimal("1901.23318")
    assert result.net == Decimal("10444.43682")


def test_krw_conversion_when_verified_rate_is_available() -> None:
    # Given: a precise foreign amount and USD/KRW rate.
    # When: the amount is converted to KRW.
    converted = convert_to_krw(Decimal("12.3456"), Decimal("1387.42"))

    # Then: multiplication direction and Decimal precision are preserved.
    assert converted == Decimal("17128.532352")


def test_krw_conversion_rejects_non_positive_rate() -> None:
    # Given: a foreign amount and an unusable zero rate.
    amount = Decimal("12.34")

    # When: conversion is attempted.
    with pytest.raises(ValueError, match="환율"):
        _ = convert_to_krw(amount, Decimal(0))

    # Then: no fabricated zero or 1:1 conversion is returned.
