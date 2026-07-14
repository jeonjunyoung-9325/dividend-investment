"""Korean financial display formatting."""

from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def money(value: Decimal, currency: str = "KRW") -> str:
    """Format an exact amount in its original currency."""
    match currency.upper():
        case "KRW":
            return f"{value:,.0f}원"
        case "USD":
            return f"${value:,.2f}"
        case "JPY":
            return f"¥{value:,.0f}"
        case code:
            return f"{value:,.2f} {code}"


def percentage(value: Decimal) -> str:
    """Format a signed percentage."""
    return f"{value:+,.2f}%"


def kst_datetime(value: datetime | None) -> str:
    """Format a timestamp in Asia/Seoul."""
    if value is None:
        return "기록 없음"
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return aware.astimezone(KST).strftime("%Y-%m-%d %H:%M KST")
