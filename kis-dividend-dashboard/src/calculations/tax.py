"""Simple withholding assumptions for estimated dividends."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TaxEstimate:
    """Simple estimate, not a final tax determination."""

    gross: Decimal
    tax_rate: Decimal
    withholding: Decimal
    net: Decimal


def estimate_tax(gross: Decimal, tax_rate: Decimal) -> TaxEstimate:
    """Apply a bounded user-configured withholding rate."""
    if gross < 0:
        msg = "세전 금액은 음수일 수 없습니다."
        raise ValueError(msg)
    if tax_rate < 0 or tax_rate > 1:
        msg = "세율은 0 이상 1 이하여야 합니다."
        raise ValueError(msg)
    withholding = gross * tax_rate
    return TaxEstimate(
        gross=gross, tax_rate=tax_rate, withholding=withholding, net=gross - withholding
    )
