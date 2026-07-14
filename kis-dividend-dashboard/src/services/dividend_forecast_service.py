from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.calculations.dividend_forecast import ForecastMethod, forecast_dividend
from src.calculations.tax import estimate_tax
from src.schemas import DividendHistoryItem

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

    from src.models import DividendPayment, PortfolioSnapshot


@dataclass(frozen=True, slots=True)
class ForecastTaxRates:
    domestic: Decimal
    us: Decimal
    overseas: Decimal


def forecast_rows(
    positions: tuple[PortfolioSnapshot, ...],
    payments: tuple[DividendPayment, ...],
    *,
    as_of: date,
    tax_rates: ForecastTaxRates,
    symbol_overrides: dict[str, tuple[Decimal | None, ForecastMethod | None, Decimal | None]]
    | None = None,
) -> tuple[dict[str, object], ...]:
    grouped: dict[tuple[str, str, str], list[DividendHistoryItem]] = {}
    for payment in payments:
        if payment.amount_per_share is None or payment.amount_per_share <= 0:
            continue
        key = (payment.market, payment.exchange, payment.symbol)
        grouped.setdefault(key, []).append(
            DividendHistoryItem(
                payment_date=payment.payment_date,
                amount_per_share=payment.amount_per_share,
                currency=payment.currency,
                source=payment.source,
            )
        )
    rows: list[dict[str, object]] = []
    for position in positions:
        key = (position.market, position.exchange, position.symbol)
        override = (symbol_overrides or {}).get(position.symbol, (None, None, None))
        forecast = forecast_dividend(
            grouped.get(key, []),
            position.quantity,
            as_of,
            method=override[1],
            manual_annual_per_share=override[2],
        )
        rate = override[0] or _tax_rate(position.market, position.exchange, tax_rates)
        tax = (
            estimate_tax(forecast.gross_amount, rate) if forecast.gross_amount is not None else None
        )
        rows.append(
            {
                "종목": position.name,
                "종목코드": position.symbol,
                "예측 방식": forecast.method.value if forecast.method else "예측 불가",
                "지급 주기": forecast.frequency.value,
                "표본 수": forecast.sample_count,
                "연간 예상 지급 횟수": forecast.annual_payments,
                "예상 연간 주당 배당금": forecast.annual_per_share,
                "적용 가정 세율": rate,
                "예상 세전": tax.gross if tax else None,
                "예상 원천징수": tax.withholding if tax else None,
                "예상 세후": tax.net if tax else None,
                "통화": position.currency,
                "신뢰도": forecast.confidence,
                "마지막 데이터": forecast.data_end,
                "출처": forecast.source,
            }
        )
    return tuple(rows)


def _tax_rate(
    market: str,
    exchange: str,
    rates: ForecastTaxRates,
) -> Decimal:
    if market == "domestic":
        return rates.domestic
    return rates.us if exchange in {"NASD", "NAS", "NYSE", "AMEX"} else rates.overseas
