from datetime import date
from decimal import Decimal

from src.calculations.dividend_projection import (
    AssetProjectionInput,
    InvestmentRuleInput,
    ScenarioName,
    build_projection,
)


def _asset(
    symbol: str,
    *,
    shares: str,
    price_krw: str,
    annual_dividend_krw: str,
    annual_payments: int = 12,
) -> AssetProjectionInput:
    return AssetProjectionInput(
        market="overseas",
        exchange="NASD",
        symbol=symbol,
        name=symbol,
        shares=Decimal(shares),
        price_krw=Decimal(price_krw),
        annual_dividend_per_share_krw=Decimal(annual_dividend_krw),
        annual_payments=annual_payments,
        last_payment_month=7,
        tax_rate=Decimal("0.15"),
    )


def test_monthly_investment_and_net_dividend_buy_fractional_jepq() -> None:
    # Given: a monthly JEPI rule and a JEPQ holding receiving monthly dividends.
    assets = (
        _asset("JEPI", shares="10", price_krw="10000", annual_dividend_krw="1200"),
        _asset("JEPQ", shares="1", price_krw="20000", annual_dividend_krw="2400"),
    )
    rules = (
        InvestmentRuleInput(
            market="overseas",
            exchange="NASD",
            symbol="JEPI",
            rule_type="monthly",
            amount_krw=Decimal(10000),
        ),
    )

    # When: the base scenario projects two months with JEPQ reinvestment.
    result = build_projection(
        assets,
        rules,
        as_of=date(2026, 7, 15),
        months=2,
        reinvest_in_jepq=True,
        scenarios=(ScenarioName.BASE,),
    )

    # Then: the rule buys before dividends and net dividends buy JEPQ after payment.
    first, second = result.points
    assert first.regular_investment_krw == Decimal(10000)
    assert first.gross_dividend_krw == Decimal(1300)
    assert first.net_dividend_krw == Decimal("1105.00")
    assert first.jepq_shares == Decimal("1.05525")
    assert second.gross_dividend_krw.quantize(Decimal("0.00001")) == Decimal("1410.80398")


def test_daily_rules_count_weekdays_and_weekly_rules_count_selected_day() -> None:
    # Given: August 2026 daily cash and Tuesday one-share rules.
    asset = _asset("JEPQ", shares="1", price_krw="10000", annual_dividend_krw="0")
    rules = (
        InvestmentRuleInput(
            market="overseas",
            exchange="NASD",
            symbol="JEPQ",
            rule_type="daily",
            amount_krw=Decimal(1000),
        ),
        InvestmentRuleInput(
            market="overseas",
            exchange="NASD",
            symbol="JEPQ",
            rule_type="weekly",
            shares=Decimal(1),
            weekday=1,
        ),
    )

    # When: one month is projected without dividend reinvestment.
    result = build_projection(
        (asset,),
        rules,
        as_of=date(2026, 7, 31),
        months=1,
        reinvest_in_jepq=False,
        scenarios=(ScenarioName.BASE,),
    )

    # Then: 21 weekdays and four Tuesdays are applied, not 31 calendar days.
    point = result.points[0]
    assert point.regular_investment_krw == Decimal(61000)
    assert point.jepq_shares == Decimal("7.1")


def test_scenario_dividends_are_ordered_without_new_investment() -> None:
    # Given: one monthly dividend asset and no contribution rules.
    asset = _asset("JEPQ", shares="10", price_krw="10000", annual_dividend_krw="1200")

    # When: all scenarios are projected for five years.
    result = build_projection(
        (asset,),
        (),
        as_of=date(2026, 7, 15),
        months=60,
        reinvest_in_jepq=False,
    )

    # Then: annual payout assumptions keep conservative below base below optimistic.
    totals = {
        scenario: sum(
            (point.net_dividend_krw for point in result.points if point.scenario is scenario),
            Decimal(0),
        )
        for scenario in ScenarioName
    }
    assert totals[ScenarioName.CONSERVATIVE] < totals[ScenarioName.BASE]
    assert totals[ScenarioName.BASE] < totals[ScenarioName.OPTIMISTIC]


def test_monthly_points_and_annual_rows_have_matching_net_totals() -> None:
    # Given: a fixed monthly dividend over an 18-month horizon.
    asset = _asset("JEPQ", shares="2", price_krw="10000", annual_dividend_krw="1200")

    # When: the base projection is aggregated by calendar year.
    result = build_projection(
        (asset,),
        (),
        as_of=date(2026, 7, 15),
        months=18,
        reinvest_in_jepq=False,
        scenarios=(ScenarioName.BASE,),
    )

    # Then: monthly and yearly totals are identical and span three calendar years.
    monthly_total = sum((point.net_dividend_krw for point in result.points), Decimal(0))
    annual_total = sum((row.net_dividend_krw for row in result.annual), Decimal(0))
    assert monthly_total == annual_total
    assert [row.year for row in result.annual] == [2026, 2027, 2028]


def test_more_than_monthly_payments_preserve_annual_dividend_total() -> None:
    # Given: a weekly-paying asset whose annual dividend is already normalized.
    asset = _asset(
        "NVDY",
        shares="1",
        price_krw="10000",
        annual_dividend_krw="1200",
        annual_payments=52,
    )

    # When: twelve monthly projection buckets are calculated.
    result = build_projection(
        (asset,),
        (),
        as_of=date(2026, 7, 15),
        months=12,
        reinvest_in_jepq=False,
        scenarios=(ScenarioName.BASE,),
    )

    # Then: weekly frequency does not divide the annual total by 52 a second time.
    gross_total = sum((point.gross_dividend_krw for point in result.points), Decimal(0))
    assert gross_total == Decimal(1200)


def test_missing_jepq_price_skips_reinvestment_with_visible_warning() -> None:
    # Given: dividend income exists but JEPQ has no usable price.
    asset = _asset("JEPI", shares="10", price_krw="10000", annual_dividend_krw="1200")

    # When: JEPQ reinvestment is requested.
    result = build_projection(
        (asset,),
        (),
        as_of=date(2026, 7, 15),
        months=1,
        reinvest_in_jepq=True,
        scenarios=(ScenarioName.BASE,),
    )

    # Then: income remains visible while reinvestment is not fabricated.
    assert result.points[0].reinvested_krw == Decimal(0)
    assert result.warnings == ("JEPQ 가격이 없어 배당 재투자를 계산하지 못했습니다.",)
