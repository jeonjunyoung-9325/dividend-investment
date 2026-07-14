"""Currency conversion without binary floating-point arithmetic."""

from decimal import Decimal


def convert_to_krw(amount: Decimal, krw_per_unit: Decimal) -> Decimal:
    """Convert an original-currency amount using a positive KRW quote."""
    if krw_per_unit <= 0:
        msg = "환율은 0보다 커야 합니다."
        raise ValueError(msg)
    return amount * krw_per_unit
