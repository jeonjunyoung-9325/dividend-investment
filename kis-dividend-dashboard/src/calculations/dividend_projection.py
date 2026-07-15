"""Monthly dividend projections with contributions and JEPQ reinvestment."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from enum import StrEnum
from typing import Final, Literal

ZERO: Final = Decimal(0)
ONE: Final = Decimal(1)
MONTHS_PER_YEAR: Final = Decimal(12)
MONTH_COUNT: Final = 12
WEEKDAY_COUNT: Final = 5
InvestmentRuleType = Literal["daily", "weekly", "monthly"]


class ScenarioName(StrEnum):
    """Projection scenario exposed to the dashboard."""

    CONSERVATIVE = "conservative"
    BASE = "base"
    OPTIMISTIC = "optimistic"


@dataclass(frozen=True, slots=True)
class ScenarioAssumption:
    """Annual price and dividend-per-share growth assumptions."""

    price_growth: Decimal
    payout_growth: Decimal


DEFAULT_ASSUMPTIONS: Final = {
    ScenarioName.CONSERVATIVE: ScenarioAssumption(Decimal(0), Decimal("-0.05")),
    ScenarioName.BASE: ScenarioAssumption(Decimal("0.03"), Decimal(0)),
    ScenarioName.OPTIMISTIC: ScenarioAssumption(Decimal("0.07"), Decimal("0.05")),
}


@dataclass(frozen=True, slots=True)
class AssetProjectionInput:
    """Validated current holding and annual dividend basis."""

    market: str
    exchange: str
    symbol: str
    name: str
    shares: Decimal
    price_krw: Decimal
    annual_dividend_per_share_krw: Decimal
    annual_payments: int
    last_payment_month: int
    tax_rate: Decimal


@dataclass(frozen=True, slots=True)
class InvestmentRuleInput:
    """One recurring purchase rule applied to a holding."""

    market: str
    exchange: str
    symbol: str
    rule_type: InvestmentRuleType
    amount_krw: Decimal | None = None
    shares: Decimal | None = None
    weekday: int | None = None


@dataclass(frozen=True, slots=True)
class ProjectionPoint:
    """One scenario-month result."""

    scenario: ScenarioName
    month: date
    gross_dividend_krw: Decimal
    tax_krw: Decimal
    net_dividend_krw: Decimal
    regular_investment_krw: Decimal
    reinvested_krw: Decimal
    jepq_shares: Decimal
    portfolio_value_krw: Decimal


@dataclass(frozen=True, slots=True)
class ProjectionAnnual:
    """Calendar-year projection totals."""

    scenario: ScenarioName
    year: int
    gross_dividend_krw: Decimal
    tax_krw: Decimal
    net_dividend_krw: Decimal
    regular_investment_krw: Decimal
    reinvested_krw: Decimal


@dataclass(frozen=True, slots=True)
class ProjectionResult:
    """Complete monthly and annual scenario projection."""

    points: tuple[ProjectionPoint, ...]
    annual: tuple[ProjectionAnnual, ...]
    warnings: tuple[str, ...]


def build_projection(
    assets: tuple[AssetProjectionInput, ...],
    rules: tuple[InvestmentRuleInput, ...],
    *,
    as_of: date,
    months: int,
    reinvest_in_jepq: bool,
    scenarios: tuple[ScenarioName, ...] = tuple(ScenarioName),
) -> ProjectionResult:
    """Project monthly dividends from current shares without using float arithmetic."""
    warnings: list[str] = []
    points: list[ProjectionPoint] = []
    assets_by_key = {_asset_key(asset): asset for asset in assets}
    jepq = next((asset for asset in assets if asset.symbol == "JEPQ"), None)
    can_reinvest = reinvest_in_jepq and jepq is not None and jepq.price_krw > ZERO
    if reinvest_in_jepq and not can_reinvest:
        warnings.append("JEPQ 가격이 없어 배당 재투자를 계산하지 못했습니다.")

    for scenario in scenarios:
        shares = {_asset_key(asset): asset.shares for asset in assets}
        assumption = DEFAULT_ASSUMPTIONS[scenario]
        for month_index in range(1, months + 1):
            projected_month = _add_months(as_of, month_index)
            price_factor = _annual_factor(assumption.price_growth, month_index - 1)
            payout_factor = _annual_factor(assumption.payout_growth, month_index - 1)
            regular_investment = ZERO

            for rule in rules:
                asset = assets_by_key.get(_asset_key(rule))
                if asset is None or asset.price_krw <= ZERO:
                    continue
                price = asset.price_krw * price_factor
                cash, added_shares = _rule_purchase(rule, projected_month, price)
                regular_investment += cash
                shares[_asset_key(asset)] += added_shares

            gross = ZERO
            tax = ZERO
            for asset in assets:
                if not _pays_in_month(asset, projected_month):
                    continue
                payment = (
                    shares[_asset_key(asset)]
                    * asset.annual_dividend_per_share_krw
                    / Decimal(_projection_payment_count(asset.annual_payments))
                    * payout_factor
                )
                gross += payment
                tax += payment * asset.tax_rate

            net = gross - tax
            reinvested = ZERO
            if can_reinvest and jepq is not None and net > ZERO:
                jepq_price = jepq.price_krw * price_factor
                shares[_asset_key(jepq)] += net / jepq_price
                reinvested = net

            portfolio_value = sum(
                (shares[_asset_key(asset)] * asset.price_krw * price_factor for asset in assets),
                ZERO,
            )
            points.append(
                ProjectionPoint(
                    scenario=scenario,
                    month=projected_month,
                    gross_dividend_krw=gross,
                    tax_krw=tax,
                    net_dividend_krw=net,
                    regular_investment_krw=regular_investment,
                    reinvested_krw=reinvested,
                    jepq_shares=(shares[_asset_key(jepq)] if jepq is not None else ZERO),
                    portfolio_value_krw=portfolio_value,
                )
            )

    return ProjectionResult(tuple(points), _annual_rows(points), tuple(warnings))


def _annual_factor(rate: Decimal, completed_months: int) -> Decimal:
    if completed_months == 0 or rate == ZERO:
        return ONE
    with localcontext() as context:
        context.prec = 28
        return (ONE + rate) ** (Decimal(completed_months) / MONTHS_PER_YEAR)


def _asset_key(
    asset: AssetProjectionInput | InvestmentRuleInput,
) -> tuple[str, str, str]:
    return asset.market, asset.exchange, asset.symbol


def _add_months(as_of: date, offset: int) -> date:
    absolute_month = as_of.year * 12 + as_of.month - 1 + offset
    return date(absolute_month // 12, absolute_month % 12 + 1, 1)


def _rule_purchase(
    rule: InvestmentRuleInput, projected_month: date, price_krw: Decimal
) -> tuple[Decimal, Decimal]:
    match rule.rule_type:
        case "daily":
            occurrences = _weekday_count(projected_month)
        case "weekly":
            occurrences = _selected_weekday_count(projected_month, rule.weekday or 0)
        case "monthly":
            occurrences = 1

    if rule.amount_krw is not None:
        cash = rule.amount_krw * occurrences
        return cash, cash / price_krw
    if rule.shares is not None:
        added_shares = rule.shares * occurrences
        return added_shares * price_krw, added_shares
    return ZERO, ZERO


def _weekday_count(month: date) -> int:
    return sum(
        1
        for day in range(1, calendar.monthrange(month.year, month.month)[1] + 1)
        if date(month.year, month.month, day).weekday() < WEEKDAY_COUNT
    )


def _selected_weekday_count(month: date, weekday: int) -> int:
    return sum(
        1
        for day in range(1, calendar.monthrange(month.year, month.month)[1] + 1)
        if date(month.year, month.month, day).weekday() == weekday
    )


def _pays_in_month(asset: AssetProjectionInput, month: date) -> bool:
    if asset.annual_dividend_per_share_krw <= ZERO or asset.annual_payments <= 0:
        return False
    if asset.annual_payments >= MONTH_COUNT:
        return True
    interval = MONTH_COUNT // asset.annual_payments
    return (month.month - asset.last_payment_month) % interval == 0


def _projection_payment_count(annual_payments: int) -> int:
    return min(annual_payments, MONTH_COUNT)


def _annual_rows(points: list[ProjectionPoint]) -> tuple[ProjectionAnnual, ...]:
    grouped: dict[tuple[ScenarioName, int], list[ProjectionPoint]] = {}
    for point in points:
        grouped.setdefault((point.scenario, point.month.year), []).append(point)
    return tuple(
        ProjectionAnnual(
            scenario=scenario,
            year=year,
            gross_dividend_krw=sum((point.gross_dividend_krw for point in rows), ZERO),
            tax_krw=sum((point.tax_krw for point in rows), ZERO),
            net_dividend_krw=sum((point.net_dividend_krw for point in rows), ZERO),
            regular_investment_krw=sum((point.regular_investment_krw for point in rows), ZERO),
            reinvested_krw=sum((point.reinvested_krw for point in rows), ZERO),
        )
        for (scenario, year), rows in sorted(grouped.items(), key=lambda item: item[0])
    )
