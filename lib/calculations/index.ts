import Decimal from "decimal.js";
import { addMonths, differenceInMilliseconds, endOfMonth, startOfMonth } from "date-fns";
import { scenarioGrowthRates } from "@/lib/catalog/assets";
import {
  ActualDividend,
  Asset,
  AssumptionType,
  DividendAssumption,
  DividendFrequency,
  DividendWithAsset,
  FxRate,
  Goal,
  HoldingWithAsset,
  MarketQuote,
  ProjectionScenario,
  RuleWithAsset,
  AppSettings,
} from "@/types";
import { toDecimal } from "@/lib/utils";

const ESTIMATED_OVERSEAS_WITHHOLDING_RATE = new Decimal(0.15);

function getDefaultQuarterlyMonths() {
  return [3, 6, 9, 12];
}

function getDistributionMonths(assumption?: DividendAssumption) {
  if (!assumption?.distribution_months?.length) {
    return getDefaultQuarterlyMonths();
  }

  return assumption.distribution_months;
}

function countWeekdayInMonth(date: Date, weekday: number) {
  const month = date.getMonth();
  const year = date.getFullYear();
  const cursor = new Date(year, month, 1);
  let count = 0;

  while (cursor.getMonth() === month) {
    if (cursor.getDay() === weekday) {
      count += 1;
    }
    cursor.setDate(cursor.getDate() + 1);
  }

  return count;
}

function getRuleExecutionsForMonth(rule: RuleWithAsset, date: Date) {
  if (rule.rule_type === "monthly") {
    return 1;
  }

  if (rule.rule_type === "weekly") {
    return countWeekdayInMonth(date, rule.weekday ?? 1);
  }

  return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
}

export function getEffectiveExchangeRate(
  fxRates: FxRate[],
  fallbackExchangeRate: Decimal.Value,
  useAutoExchangeRate = true,
) {
  const usdKrw = fxRates
    .filter((row) => row.pair === "USD/KRW")
    .sort((a, b) => new Date(b.fetched_at).getTime() - new Date(a.fetched_at).getTime())[0];

  if (!useAutoExchangeRate && !usdKrw) {
    return toDecimal(fallbackExchangeRate);
  }

  return toDecimal(usdKrw?.rate ?? fallbackExchangeRate);
}

export function getLatestQuoteForAsset(asset: Asset, marketQuotes: MarketQuote[]) {
  return marketQuotes
    .filter((row) => row.asset_id === asset.id)
    .sort((a, b) => new Date(b.fetched_at).getTime() - new Date(a.fetched_at).getTime())[0];
}

export function calculateCurrentValueKRW(params: {
  shares: Decimal.Value;
  market: "US" | "KR";
  currentPrice: Decimal.Value;
  exchangeRate: Decimal.Value;
}) {
  const shares = toDecimal(params.shares);
  const currentPrice = toDecimal(params.currentPrice);
  const exchangeRate = toDecimal(params.exchangeRate);

  if (params.market === "US") {
    return shares.mul(currentPrice).mul(exchangeRate);
  }

  return shares.mul(currentPrice);
}

export function getEffectiveHoldingShares(holding: HoldingWithAsset, settings: AppSettings) {
  void settings;
  return holding.synced_shares ?? "0";
}

export function getEffectiveHoldingAverageCostKRW(holding: HoldingWithAsset, settings: AppSettings) {
  void settings;
  return holding.synced_average_cost_krw;
}

export function calculateEffectiveHoldingValueKRW(params: {
  holding: HoldingWithAsset;
  settings: AppSettings;
  marketQuotes: MarketQuote[];
  exchangeRate: Decimal.Value;
}) {
  if (params.holding.synced_value_krw !== null) {
    return toDecimal(params.holding.synced_value_krw);
  }

  const quote = getLatestQuoteForAsset(params.holding.asset, params.marketQuotes);
  return calculateCurrentValueKRW({
    shares: getEffectiveHoldingShares(params.holding, params.settings),
    market: params.holding.asset.market,
    currentPrice: quote?.price ?? 0,
    exchangeRate: params.exchangeRate,
  });
}

function assumptionTypeToAnnual(params: {
  assumptionType: AssumptionType;
  annualDividendPerShare: Decimal.Value | null;
  quarterlyDividendPerShare: Decimal.Value | null;
  monthlyDividendPerShare: Decimal.Value | null;
  weeklyDividendPerShare: Decimal.Value | null;
}) {
  if (params.assumptionType === "annual_per_share") {
    return toDecimal(params.annualDividendPerShare);
  }

  if (params.assumptionType === "quarterly_per_share") {
    return toDecimal(params.quarterlyDividendPerShare).mul(4);
  }

  if (params.assumptionType === "monthly_per_share") {
    return toDecimal(params.monthlyDividendPerShare).mul(12);
  }

  if (params.assumptionType === "weekly_per_share") {
    return toDecimal(params.weeklyDividendPerShare).mul(52);
  }

  return new Decimal(0);
}

function scaleAssumption(assumption: DividendAssumption | undefined, factor: Decimal) {
  if (!assumption) {
    return undefined;
  }

  return {
    ...assumption,
    annual_dividend_per_share: assumption.annual_dividend_per_share
      ? toDecimal(assumption.annual_dividend_per_share).mul(factor).toFixed(8)
      : null,
    quarterly_dividend_per_share: assumption.quarterly_dividend_per_share
      ? toDecimal(assumption.quarterly_dividend_per_share).mul(factor).toFixed(8)
      : null,
    monthly_dividend_per_share: assumption.monthly_dividend_per_share
      ? toDecimal(assumption.monthly_dividend_per_share).mul(factor).toFixed(8)
      : null,
    weekly_dividend_per_share: assumption.weekly_dividend_per_share
      ? toDecimal(assumption.weekly_dividend_per_share).mul(factor).toFixed(8)
      : null,
  };
}

export function calculateAnnualExpectedDividend(params: {
  shares: Decimal.Value;
  asset: Asset;
  assumption?: DividendAssumption;
  exchangeRate: Decimal.Value;
}) {
  const shares = toDecimal(params.shares);
  const exchangeRate = toDecimal(params.exchangeRate);
  const assumption = params.assumption;

  if (!assumption || !assumption.is_active) {
    return new Decimal(0);
  }

  const nativeAnnual = assumptionTypeToAnnual({
    assumptionType: assumption.assumption_type,
    annualDividendPerShare: assumption.annual_dividend_per_share,
    quarterlyDividendPerShare: assumption.quarterly_dividend_per_share,
    monthlyDividendPerShare: assumption.monthly_dividend_per_share,
    weeklyDividendPerShare: assumption.weekly_dividend_per_share,
  });

  if (params.asset.market === "US") {
    return shares.mul(nativeAnnual).mul(exchangeRate);
  }

  return shares.mul(nativeAnnual);
}

export function calculateMonthlyExpectedDividend(params: {
  shares: Decimal.Value;
  asset: Asset;
  assumption?: DividendAssumption;
  exchangeRate: Decimal.Value;
  monthDate?: Date;
}) {
  const shares = toDecimal(params.shares);
  const exchangeRate = toDecimal(params.exchangeRate);
  const assumption = params.assumption;
  const monthDate = params.monthDate ?? new Date();

  if (!assumption || !assumption.is_active) {
    return new Decimal(0);
  }

  let nativeMonthly = new Decimal(0);

  if (assumption.assumption_type === "annual_per_share") {
    nativeMonthly = toDecimal(assumption.annual_dividend_per_share).div(12);
  } else if (assumption.assumption_type === "quarterly_per_share") {
    nativeMonthly = getDistributionMonths(assumption).includes(monthDate.getMonth() + 1)
      ? toDecimal(assumption.quarterly_dividend_per_share)
      : new Decimal(0);
  } else if (assumption.assumption_type === "monthly_per_share") {
    nativeMonthly = toDecimal(assumption.monthly_dividend_per_share);
  } else if (assumption.assumption_type === "weekly_per_share") {
    nativeMonthly = toDecimal(assumption.weekly_dividend_per_share).mul(countWeekdayInMonth(monthDate, 5));
  }

  if (params.asset.market === "US") {
    return shares.mul(nativeMonthly).mul(exchangeRate);
  }

  return shares.mul(nativeMonthly);
}

export function calculatePortfolioWeights(
  holdings: Array<{
    ticker: string;
    valueKRW: Decimal.Value;
    color: string;
  }>,
) {
  const total = holdings.reduce((acc, holding) => acc.plus(toDecimal(holding.valueKRW)), new Decimal(0));

  return holdings.map((holding) => {
    const value = toDecimal(holding.valueKRW);

    return {
      ...holding,
      weight: total.gt(0) ? value.div(total).mul(100) : new Decimal(0),
    };
  });
}

export function calculateLiveDividendCounter(params: {
  monthlyExpectedDividendKRW: Decimal.Value;
  now?: Date;
  animationEnabled?: boolean;
}) {
  const now = params.now ?? new Date();
  const monthlyExpectedDividend = toDecimal(params.monthlyExpectedDividendKRW);
  const monthStart = startOfMonth(now);
  const monthEnd = endOfMonth(now);
  const elapsedMs = Math.max(0, differenceInMilliseconds(now, monthStart));
  const totalMs = Math.max(1, differenceInMilliseconds(monthEnd, monthStart));
  const progress = new Decimal(elapsedMs).div(totalMs);
  const accumulated = monthlyExpectedDividend.mul(progress);
  const secondsInMonth = new Decimal(totalMs).div(1000);

  return {
    accumulated,
    dailyRate: monthlyExpectedDividend.div(Math.max(1, monthEnd.getDate())),
    hourlyRate: monthlyExpectedDividend.div(secondsInMonth).mul(3600),
    minutelyRate: monthlyExpectedDividend.div(secondsInMonth).mul(60),
    animationEnabled: params.animationEnabled ?? true,
  };
}

export function sumActualDividendsByMonth(dividends: ActualDividend[], now = new Date(), taxMode: string = "gross") {
  return dividends
    .filter((dividend) => {
      const paidDate = new Date(dividend.paid_date);
      return paidDate.getFullYear() === now.getFullYear() && paidDate.getMonth() === now.getMonth();
    })
    .reduce((acc, row) => acc.plus(getActualDividendDisplayAmount(row, taxMode)), new Decimal(0));
}

export function sumActualDividendsByYear(dividends: ActualDividend[], year = new Date().getFullYear(), taxMode: string = "gross") {
  return dividends
    .filter((dividend) => new Date(dividend.paid_date).getFullYear() === year)
    .reduce((acc, row) => acc.plus(getActualDividendDisplayAmount(row, taxMode)), new Decimal(0));
}

export function calculateGoalProgress(params: {
  goal: Goal | undefined;
  monthlyExpectedDividendKRW: Decimal.Value;
  rules: RuleWithAsset[];
  assumptions: DividendAssumption[];
  exchangeRate: Decimal.Value;
  marketQuotes: MarketQuote[];
  monthDate?: Date;
}) {
  const goalAmount = toDecimal(params.goal?.target_amount_krw ?? 0);
  const current = toDecimal(params.monthlyExpectedDividendKRW);
  const progress = goalAmount.gt(0) ? Decimal.min(new Decimal(100), current.div(goalAmount).mul(100)) : new Decimal(0);
  const monthDate = params.monthDate ?? new Date();

  const monthlyGrowth = params.rules.reduce((acc, rule) => {
    if (!rule.enabled) {
      return acc;
    }

    const quote = getLatestQuoteForAsset(rule.asset, params.marketQuotes);
    const price = toDecimal(quote?.price ?? 0);
    if (price.lte(0)) {
      return acc;
    }

    const executions = getRuleExecutionsForMonth(rule, monthDate);
    const assumption = params.assumptions.find((item) => item.asset_id === rule.asset_id && item.is_active);

    let addedShares = new Decimal(0);
    if (rule.shares) {
      addedShares = toDecimal(rule.shares).mul(executions);
    } else if (rule.amount_krw) {
      const amount = toDecimal(rule.amount_krw).mul(executions);
      addedShares =
        rule.asset.market === "US" ? amount.div(price.mul(params.exchangeRate)) : amount.div(price);
    }

    return acc.plus(
      calculateMonthlyExpectedDividend({
        shares: addedShares,
        asset: rule.asset,
        assumption,
        exchangeRate: params.exchangeRate,
        monthDate,
      }),
    );
  }, new Decimal(0));

  const remaining = Decimal.max(goalAmount.minus(current), 0);
  const estimatedMonths = monthlyGrowth.gt(0) ? remaining.div(monthlyGrowth).ceil().toNumber() : null;

  return {
    progress,
    goalAmount,
    estimatedArrival: estimatedMonths !== null ? addMonths(new Date(), estimatedMonths) : null,
    monthlyGrowth,
  };
}

export function estimateActualDividendTax(dividend: ActualDividend) {
  if (dividend.tax_amount_krw !== null) {
    return toDecimal(dividend.tax_amount_krw);
  }

  if (dividend.source === "kis_overseas_rights_balance") {
    return toDecimal(dividend.gross_amount_krw)
      .mul(ESTIMATED_OVERSEAS_WITHHOLDING_RATE)
      .toDecimalPlaces(2, Decimal.ROUND_HALF_UP);
  }

  return new Decimal(0);
}

export function getActualDividendDisplayAmount(dividend: ActualDividend, taxMode: string = "gross") {
  const gross = toDecimal(dividend.gross_amount_krw);
  if (taxMode === "gross") {
    return gross;
  }

  return Decimal.max(gross.minus(estimateActualDividendTax(dividend)), 0);
}

export function groupActualDividendsByMonth(dividends: ActualDividend[], year: number, taxMode: string = "gross") {
  const grouped = new Map<number, Decimal>();

  for (let month = 0; month < 12; month += 1) {
    grouped.set(month, new Decimal(0));
  }

  dividends.forEach((dividend) => {
    const paidDate = new Date(dividend.paid_date);
    if (paidDate.getFullYear() !== year) {
      return;
    }
    grouped.set(
      paidDate.getMonth(),
      (grouped.get(paidDate.getMonth()) ?? new Decimal(0)).plus(getActualDividendDisplayAmount(dividend, taxMode)),
    );
  });

  return Array.from(grouped.entries()).map(([month, amount]) => ({
    month,
    amount,
  }));
}

export function getDividendContributionByTicker(dividends: DividendWithAsset[], taxMode: string = "gross") {
  const grouped = new Map<string, Decimal>();

  dividends.forEach((dividend) => {
    const key = dividend.asset.ticker;
    grouped.set(key, (grouped.get(key) ?? new Decimal(0)).plus(getActualDividendDisplayAmount(dividend, taxMode)));
  });

  return Array.from(grouped.entries()).map(([ticker, amount]) => ({
    ticker,
    amount,
    color: "#6b7280",
  }));
}

export function getNextDividendDate(
  frequency: DividendFrequency,
  now = new Date(),
  assumption?: DividendAssumption,
) {
  const year = now.getFullYear();
  const month = now.getMonth();

  if (frequency === "none") {
    return null;
  }

  if (frequency === "weekly") {
    const next = new Date(now);
    const day = next.getDay();
    const delta = day <= 5 ? 5 - day : 12 - day;
    next.setDate(now.getDate() + delta);
    next.setHours(9, 0, 0, 0);
    return next;
  }

  if (frequency === "monthly") {
    const next = new Date(year, month, 15, 9, 0, 0, 0);
    if (next <= now) {
      return new Date(year, month + 1, 15, 9, 0, 0, 0);
    }
    return next;
  }

  const quarterlyMonths = getDistributionMonths(assumption).map((value) => value - 1);
  for (const quarterlyMonth of quarterlyMonths) {
    const candidate = new Date(year, quarterlyMonth, 15, 9, 0, 0, 0);
    if (candidate > now) {
      return candidate;
    }
  }

  return new Date(year + 1, quarterlyMonths[0] ?? 2, 15, 9, 0, 0, 0);
}

export function buildProjectionSchedule(params: {
  holdings: HoldingWithAsset[];
  rules: RuleWithAsset[];
  assumptions: DividendAssumption[];
  marketQuotes: MarketQuote[];
  settings: AppSettings;
  exchangeRate: Decimal.Value;
  years: number;
  scenario: ProjectionScenario;
  reinvest: boolean;
}) {
  const growthRate = toDecimal(scenarioGrowthRates[params.scenario]);
  const exchangeRate = toDecimal(params.exchangeRate);
  const positions = new Map(
    params.holdings.map((holding) => [holding.asset.ticker, toDecimal(getEffectiveHoldingShares(holding, params.settings))]),
  );
  const months = params.years * 12;
  const monthlyRows: Array<{
    monthLabel: string;
    expectedDividend: Decimal;
    portfolioValue: Decimal;
  }> = [];

  for (let index = 0; index < months; index += 1) {
    const currentDate = addMonths(new Date(), index);
    const growthFactor = new Decimal(1).plus(growthRate).pow(index / 12);

    params.rules.forEach((rule) => {
      if (!rule.enabled) {
        return;
      }

      const quote = getLatestQuoteForAsset(rule.asset, params.marketQuotes);
      const basePrice = toDecimal(quote?.price ?? 0);
      if (basePrice.lte(0)) {
        return;
      }

      const grownPrice = basePrice.mul(growthFactor);
      const executions = getRuleExecutionsForMonth(rule, currentDate);
      let additionalShares = new Decimal(0);

      if (rule.shares) {
        additionalShares = toDecimal(rule.shares).mul(executions);
      } else if (rule.amount_krw) {
        const amount = toDecimal(rule.amount_krw).mul(executions);
        additionalShares =
          rule.asset.market === "US" ? amount.div(grownPrice.mul(exchangeRate)) : amount.div(grownPrice);
      }

      positions.set(rule.asset.ticker, (positions.get(rule.asset.ticker) ?? new Decimal(0)).plus(additionalShares));
    });

    let monthlyDividend = new Decimal(0);
    let portfolioValue = new Decimal(0);

    params.holdings.forEach((holding) => {
      const ticker = holding.asset.ticker;
      const shares = positions.get(ticker) ?? new Decimal(0);
      const quote = getLatestQuoteForAsset(holding.asset, params.marketQuotes);
      const basePrice = toDecimal(quote?.price ?? 0);
      const grownPrice = basePrice.mul(growthFactor);
      const assumption = scaleAssumption(
        params.assumptions.find((item) => item.asset_id === holding.asset_id && item.is_active),
        growthFactor,
      );

      portfolioValue = portfolioValue.plus(
        calculateCurrentValueKRW({
          shares,
          market: holding.asset.market,
          currentPrice: grownPrice,
          exchangeRate,
        }),
      );

      const assetMonthlyDividend = calculateMonthlyExpectedDividend({
        shares,
        asset: holding.asset,
        assumption,
        exchangeRate,
        monthDate: currentDate,
      });

      monthlyDividend = monthlyDividend.plus(assetMonthlyDividend);

      if (params.reinvest && assetMonthlyDividend.gt(0) && grownPrice.gt(0)) {
        const reinvestShares =
          holding.asset.market === "US"
            ? assetMonthlyDividend.div(grownPrice.mul(exchangeRate))
            : assetMonthlyDividend.div(grownPrice);
        positions.set(ticker, shares.plus(reinvestShares));
      }
    });

    monthlyRows.push({
      monthLabel: `${currentDate.getFullYear()}년 ${currentDate.getMonth() + 1}월`,
      expectedDividend: monthlyDividend,
      portfolioValue,
    });
  }

  const yearlyTotals = Array.from({ length: params.years }, (_, yearIndex) => {
    const slice = monthlyRows.slice(yearIndex * 12, yearIndex * 12 + 12);
    const totalDividend = slice.reduce((acc, row) => acc.plus(row.expectedDividend), new Decimal(0));
    return {
      yearLabel: `${new Date().getFullYear() + yearIndex}년`,
      totalDividend,
      monthlyAverage: totalDividend.div(slice.length || 1),
    };
  });

  return {
    monthlyRows,
    yearlyTotals,
  };
}

export function sumCurrentPortfolioValue(
  holdings: HoldingWithAsset[],
  marketQuotes: MarketQuote[],
  exchangeRate: Decimal.Value,
  settings: AppSettings,
) {
  return holdings.reduce((acc, holding) => {
    return acc.plus(
      calculateEffectiveHoldingValueKRW({
        holding,
        settings,
        marketQuotes,
        exchangeRate,
      }),
    );
  }, new Decimal(0));
}

export function sumMonthlyExpectedDividend(
  holdings: HoldingWithAsset[],
  assumptions: DividendAssumption[],
  exchangeRate: Decimal.Value,
  settings: AppSettings,
  monthDate = new Date(),
) {
  return holdings.reduce(
    (acc, holding) =>
      acc.plus(
        calculateMonthlyExpectedDividend({
          shares: getEffectiveHoldingShares(holding, settings),
          asset: holding.asset,
          assumption: assumptions.find((item) => item.asset_id === holding.asset_id && item.is_active),
          exchangeRate,
          monthDate,
        }),
      ),
    new Decimal(0),
  );
}

export function sumAnnualExpectedDividend(
  holdings: HoldingWithAsset[],
  assumptions: DividendAssumption[],
  exchangeRate: Decimal.Value,
  settings: AppSettings,
) {
  return holdings.reduce(
    (acc, holding) =>
      acc.plus(
        calculateAnnualExpectedDividend({
          shares: getEffectiveHoldingShares(holding, settings),
          asset: holding.asset,
          assumption: assumptions.find((item) => item.asset_id === holding.asset_id && item.is_active),
          exchangeRate,
        }),
      ),
    new Decimal(0),
  );
}

export function findNextPayoutCountdown(holdings: HoldingWithAsset[], assumptions: DividendAssumption[]) {
  const now = new Date();
  const upcomingDates = holdings
    .filter((holding) => toDecimal(holding.synced_shares ?? 0).gt(0))
    .map((holding) =>
      getNextDividendDate(
        holding.asset.dividend_frequency,
        now,
        assumptions.find((item) => item.asset_id === holding.asset_id && item.is_active),
      ),
    )
    .filter((date): date is Date => Boolean(date))
    .sort((a, b) => a.getTime() - b.getTime());

  if (!upcomingDates.length) {
    return null;
  }

  const next = upcomingDates[0];
  const diff = next.getTime() - now.getTime();
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;

  return {
    date: next,
    label: `${days}일 ${remainingHours}시간`,
  };
}
