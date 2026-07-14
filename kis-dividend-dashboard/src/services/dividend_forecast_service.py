from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from src.calculations.dividend_forecast import ForecastMethod, forecast_dividend
from src.calculations.tax import estimate_tax
from src.schemas import DividendHistoryItem

if TYPE_CHECKING:
    from datetime import date

    from src.models import DividendEvent, DividendPayment, PortfolioSnapshot


@dataclass(frozen=True, slots=True)
class ForecastTaxRates:
    domestic: Decimal
    us: Decimal
    overseas: Decimal


@dataclass(frozen=True, slots=True)
class ForecastEvidence:
    payments: tuple[DividendPayment, ...]
    events: tuple[DividendEvent, ...] = ()


def forecast_rows(
    positions: tuple[PortfolioSnapshot, ...],
    evidence: ForecastEvidence,
    *,
    as_of: date,
    tax_rates: ForecastTaxRates,
    symbol_overrides: dict[str, tuple[Decimal | None, ForecastMethod | None, Decimal | None]]
    | None = None,
) -> tuple[dict[str, object], ...]:
    grouped: dict[tuple[str, str, str], dict[tuple[date, Decimal, str], DividendHistoryItem]] = {}
    for payment in evidence.payments:
        if (
            payment.amount_per_share is None
            or payment.amount_per_share <= 0
            or payment.payment_date > as_of
        ):
            continue
        key = (payment.market, payment.exchange, payment.symbol)
        item = DividendHistoryItem(
            payment_date=payment.payment_date,
            amount_per_share=payment.amount_per_share,
            currency=payment.currency,
            source=payment.source,
        )
        grouped.setdefault(key, {})[_history_key(item)] = item
    for event in evidence.events:
        event_date = event.payment_date or event.record_date or event.ex_dividend_date
        if event_date is None or event_date > as_of or event.amount_per_share <= 0:
            continue
        key = (event.market, event.exchange, event.symbol)
        item = DividendHistoryItem(
            payment_date=event_date,
            amount_per_share=event.amount_per_share,
            currency=event.currency,
            source=event.source,
        )
        grouped.setdefault(key, {}).setdefault(_history_key(item), item)
    rows: list[dict[str, object]] = []
    for position in positions:
        key = (position.market, position.exchange, position.symbol)
        history = list(grouped.get(key, {}).values())
        override = (symbol_overrides or {}).get(position.symbol, (None, None, None))
        forecast = forecast_dividend(
            history,
            position.quantity,
            as_of,
            method=override[1],
            manual_annual_per_share=override[2],
        )
        rate = override[0] or _tax_rate(position.market, position.exchange, tax_rates)
        tax = (
            estimate_tax(forecast.gross_amount, rate) if forecast.gross_amount is not None else None
        )
        krw_rate = Decimal(1) if position.currency == "KRW" else position.krw_exchange_rate
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
                "예상 세전 원화": tax.gross * krw_rate if tax and krw_rate else None,
                "예상 세후 원화": tax.net * krw_rate if tax and krw_rate else None,
                "통화": position.currency,
                "신뢰도": forecast.confidence,
                "마지막 데이터": forecast.data_end,
                "출처": _sources(history) if history else forecast.source,
            }
        )
    return tuple(rows)


def _history_key(item: DividendHistoryItem) -> tuple[date, Decimal, str]:
    return item.payment_date, item.amount_per_share, item.currency


def _sources(history: list[DividendHistoryItem]) -> str:
    return ", ".join(dict.fromkeys(item.source for item in history))


def _tax_rate(
    market: str,
    exchange: str,
    rates: ForecastTaxRates,
) -> Decimal:
    if market == "domestic":
        return rates.domestic
    return rates.us if exchange in {"NASD", "NAS", "NYSE", "AMEX"} else rates.overseas
