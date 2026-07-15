import assert from "node:assert/strict";
import test from "node:test";
import { buildProjectionSchedule } from "../lib/calculations/index";
import type {
  AppSettings,
  Asset,
  DividendAssumption,
  HoldingWithAsset,
  MarketQuote,
  RuleWithAsset,
} from "../types/index";

const settings: AppSettings = {
  id: "settings",
  exchange_rate: "1000",
  tax_mode: "net",
  counter_animation_enabled: false,
  auto_exchange_rate_enabled: false,
  auto_broker_sync_enabled: false,
  portfolio_data_source: "api_preferred",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function asset(ticker: string, displayOrder: number): Asset {
  return {
    id: `asset-${ticker}`,
    ticker,
    name: ticker,
    market: "US",
    asset_type: "income",
    dividend_frequency: "monthly",
    default_color: "#000000",
    display_order: displayOrder,
    price_provider: "test",
    quote_symbol: ticker,
    quote_market: "NAS",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
  };
}

function holding(item: Asset, shares: string): HoldingWithAsset {
  return {
    id: `holding-${item.ticker}`,
    asset_id: item.id,
    shares: "0",
    average_cost_krw: null,
    synced_shares: shares,
    synced_average_cost_krw: null,
    synced_value_krw: null,
    last_synced_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    created_at: "2026-01-01T00:00:00Z",
    asset: item,
  };
}

function quote(item: Asset, price: string): MarketQuote {
  return {
    id: `quote-${item.ticker}`,
    asset_id: item.id,
    price,
    currency: "USD",
    provider: "test",
    fetched_at: "2026-01-01T00:00:00Z",
    is_stale: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function assumption(item: Asset, monthlyPerShare: string): DividendAssumption {
  return {
    id: `assumption-${item.ticker}`,
    asset_id: item.id,
    assumption_type: "monthly_per_share",
    annual_dividend_per_share: null,
    quarterly_dividend_per_share: null,
    monthly_dividend_per_share: monthlyPerShare,
    weekly_dividend_per_share: null,
    distribution_months: null,
    source_note: "test",
    updated_at: "2026-01-01T00:00:00Z",
    is_active: true,
  };
}

function rule(item: Asset, ruleType: "daily" | "monthly", amountKRW: string): RuleWithAsset {
  return {
    id: `rule-${item.ticker}-${ruleType}`,
    asset_id: item.id,
    rule_type: ruleType,
    amount_krw: amountKRW,
    shares: null,
    weekday: null,
    enabled: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    asset: item,
  };
}

test("실보유 수량과 월 투자 후 세후 배당을 JEPQ 수량으로 재투자한다", () => {
  const income = asset("INCOME", 1);
  const jepq = asset("JEPQ", 2);
  const projection = buildProjectionSchedule({
    holdings: [holding(income, "10"), holding(jepq, "0")],
    rules: [rule(income, "monthly", "10000")],
    assumptions: [assumption(income, "1"), assumption(jepq, "0")],
    marketQuotes: [quote(income, "10"), quote(jepq, "50")],
    settings,
    exchangeRate: "1000",
    years: 1,
    scenario: "base",
    reinvest: true,
    asOf: new Date(2026, 0, 1),
  });

  const january = projection.monthlyRows[0];
  assert.equal(january.expectedDividend.toFixed(2), "11000.00");
  assert.equal(january.estimatedTax.toFixed(2), "1650.00");
  assert.equal(january.netDividend.toFixed(2), "9350.00");
  assert.equal(january.reinvestedAmount.toFixed(2), "9350.00");
  assert.equal(january.reinvestedShares.toFixed(3), "0.187");
  assert.equal(january.regularInvestment.toFixed(0), "10000");
  assert.equal(january.portfolioValue.toFixed(0), "119350");
});

test("매일 투자 규칙은 달력일이 아니라 평일 수로 계산한다", () => {
  const income = asset("INCOME", 1);
  const projection = buildProjectionSchedule({
    holdings: [holding(income, "0")],
    rules: [rule(income, "daily", "1000")],
    assumptions: [assumption(income, "0")],
    marketQuotes: [quote(income, "10")],
    settings,
    exchangeRate: "1000",
    years: 1,
    scenario: "base",
    reinvest: false,
    asOf: new Date(2026, 0, 1),
  });

  assert.equal(projection.monthlyRows[0].regularInvestment.toFixed(0), "22000");
});

test("동일 보유 수량에서 보수보다 기준, 기준보다 긍정 예상 배당이 크다", () => {
  const income = asset("INCOME", 1);
  const params: Omit<Parameters<typeof buildProjectionSchedule>[0], "scenario"> = {
    holdings: [holding(income, "10")],
    rules: [],
    assumptions: [assumption(income, "1")],
    marketQuotes: [quote(income, "10")],
    settings,
    exchangeRate: "1000",
    years: 3,
    reinvest: false,
    asOf: new Date(2026, 0, 1),
  };

  const conservative = buildProjectionSchedule({ ...params, scenario: "conservative" });
  const base = buildProjectionSchedule({ ...params, scenario: "base" });
  const optimistic = buildProjectionSchedule({ ...params, scenario: "optimistic" });
  const conservativeTotal = conservative.yearlyTotals[2].totalNetDividend;
  const baseTotal = base.yearlyTotals[2].totalNetDividend;
  const optimisticTotal = optimistic.yearlyTotals[2].totalNetDividend;

  assert.equal(conservativeTotal.lt(baseTotal), true);
  assert.equal(baseTotal.lt(optimisticTotal), true);
});

test("JEPQ 시세가 없으면 재투자를 생략하고 이유를 반환한다", () => {
  const income = asset("INCOME", 1);
  const projection = buildProjectionSchedule({
    holdings: [holding(income, "10")],
    rules: [],
    assumptions: [assumption(income, "1")],
    marketQuotes: [quote(income, "10")],
    settings,
    exchangeRate: "1000",
    years: 1,
    scenario: "base",
    reinvest: true,
    asOf: new Date(2026, 0, 1),
  });

  assert.equal(projection.reinvestmentAvailable, false);
  assert.equal(projection.monthlyRows[0].reinvestedAmount.toFixed(0), "0");
  assert.match(projection.reinvestmentWarning ?? "", /JEPQ/);
});
