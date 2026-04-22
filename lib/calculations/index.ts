import Decimal from "decimal.js";
import { addMonths, differenceInMilliseconds, endOfMonth, startOfMonth } from "date-fns";
import { assetCatalog, scenarioGrowthRates } from "@/lib/catalog/assets";
import {
  ActualDividend,
  Asset,
  AssumptionType,
  DividendAssumption,
  DividendWithAsset,
  DividendFrequency,
  Goal,
  HoldingWithAsset,
  ProjectionScenario,
  RuleWithAsset,
} from "@/types";
import { toDecimal } from "@/lib/utils";

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
}) {
  return calculateAnnualExpectedDividend(params).div(12);
}

function assumptionTypeToAnnual(params: {
  assumptionType: AssumptionType;
  annualDividendPerShare: Decimal.Value | null;
  monthlyDividendPerShare: Decimal.Value | null;
  weeklyDividendPerShare: Decimal.Value | null;
}) {
  if (params.assumptionType === "annual_per_share") {
    return toDecimal(params.annualDividendPerShare);
  }

  if (params.assumptionType === "monthly_per_share") {
    return toDecimal(params.monthlyDividendPerShare).mul(12);
  }

  if (params.assumptionType === "weekly_per_share") {
    return toDecimal(params.weeklyDividendPerShare).mul(52);
  }

  return new Decimal(0);
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

export function sumActualDividendsByMonth(dividends: ActualDividend[], now = new Date()) {
  return dividends
    .filter((dividend) => {
      const paidDate = new Date(dividend.paid_date);
      return paidDate.getFullYear() === now.getFullYear() && paidDate.getMonth() === now.getMonth();
    })
    .reduce((acc, row) => acc.plus(toDecimal(row.gross_amount_krw)), new Decimal(0));
}

export function sumActualDividendsByYear(dividends: ActualDividend[], year = new Date().getFullYear()) {
  return dividends
    .filter((dividend) => new Date(dividend.paid_date).getFullYear() === year)
    .reduce((acc, row) => acc.plus(toDecimal(row.gross_amount_krw)), new Decimal(0));
}

export function calculateGoalProgress(params: {
  goal: Goal | undefined;
  monthlyExpectedDividendKRW: Decimal.Value;
  rules: RuleWithAsset[];
  assumptions: DividendAssumption[];
  exchangeRate: Decimal.Value;
}) {
  const goalAmount = toDecimal(params.goal?.target_amount_krw ?? 0);
  const current = toDecimal(params.monthlyExpectedDividendKRW);
  const progress = goalAmount.gt(0) ? Decimal.min(new Decimal(100), current.div(goalAmount).mul(100)) : new Decimal(0);
  const monthlyGrowth = params.rules.reduce((acc, rule) => {
    if (!rule.enabled) {
      return acc;
    }

    const ticker = rule.asset.ticker;
    const priceMeta = assetCatalog[ticker];
    const assumption = params.assumptions.find((item) => item.asset_id === rule.asset_id && item.is_active);
    const price = toDecimal(priceMeta?.currentPrice ?? 0);
    if (price.lte(0)) {
      return acc;
    }

    if (rule.amount_krw) {
      let monthlyAmount = toDecimal(rule.amount_krw);
      if (rule.rule_type === "daily") {
        monthlyAmount = monthlyAmount.mul(30);
      } else if (rule.rule_type === "weekly") {
        monthlyAmount = monthlyAmount.mul(4);
      }

      const shares =
        priceMeta?.priceCurrency === "USD"
          ? monthlyAmount.div(price.mul(toDecimal(params.exchangeRate)))
          : monthlyAmount.div(price);

      return acc.plus(
        calculateMonthlyExpectedDividend({
          shares,
          asset: rule.asset,
          assumption,
          exchangeRate: params.exchangeRate,
        }),
      );
    }

    if (rule.shares) {
      let monthlyShares = toDecimal(rule.shares);
      if (rule.rule_type === "daily") {
        monthlyShares = monthlyShares.mul(30);
      } else if (rule.rule_type === "weekly") {
        monthlyShares = monthlyShares.mul(4);
      }

      return acc.plus(
        calculateMonthlyExpectedDividend({
          shares: monthlyShares,
          asset: rule.asset,
          assumption,
          exchangeRate: params.exchangeRate,
        }),
      );
    }

    return acc;
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

export function groupActualDividendsByMonth(dividends: ActualDividend[], year: number) {
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
      (grouped.get(paidDate.getMonth()) ?? new Decimal(0)).plus(toDecimal(dividend.gross_amount_krw)),
    );
  });

  return Array.from(grouped.entries()).map(([month, amount]) => ({
    month,
    amount,
  }));
}

export function getDividendContributionByTicker(dividends: DividendWithAsset[]) {
  const grouped = new Map<string, Decimal>();

  dividends.forEach((dividend) => {
    const key = dividend.asset.ticker;
    grouped.set(key, (grouped.get(key) ?? new Decimal(0)).plus(toDecimal(dividend.gross_amount_krw)));
  });

  return Array.from(grouped.entries()).map(([ticker, amount]) => ({
    ticker,
    amount,
    color: "#6b7280",
  }));
}

export function getNextDividendDate(frequency: DividendFrequency, now = new Date()) {
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

  const quarterlyMonths = [0, 3, 6, 9];
  for (const quarterlyMonth of quarterlyMonths) {
    const candidate = new Date(year, quarterlyMonth, 15, 9, 0, 0, 0);
    if (candidate > now) {
      return candidate;
    }
  }

  return new Date(year + 1, 0, 15, 9, 0, 0, 0);
}

export function buildProjectionSchedule(params: {
  holdings: HoldingWithAsset[];
  rules: RuleWithAsset[];
  assumptions: DividendAssumption[];
  exchangeRate: Decimal.Value;
  years: number;
  scenario: ProjectionScenario;
  reinvest: boolean;
}) {
  // Projection intentionally starts from the current position snapshot.
  // We do not try to reconstruct historical ex-date holdings from actual dividend records.
  const growthRate = toDecimal(scenarioGrowthRates[params.scenario]);
  const exchangeRate = toDecimal(params.exchangeRate);
  const positions = new Map(
    params.holdings.map((holding) => [holding.asset.ticker, toDecimal(holding.shares)]),
  );
  const months = params.years * 12;
  const monthlyRows: Array<{
    monthLabel: string;
    expectedDividend: Decimal;
    portfolioValue: Decimal;
  }> = [];

  for (let index = 0; index < months; index += 1) {
    const currentDate = addMonths(new Date(), index);

    params.rules.forEach((rule) => {
      if (!rule.enabled) {
        return;
      }

      const ticker = rule.asset.ticker;
      const catalog = assetCatalog[ticker];
      if (!catalog) {
        return;
      }

      const price = toDecimal(catalog.currentPrice);
      let additionalShares = new Decimal(0);

      if (rule.shares) {
        additionalShares = toDecimal(rule.shares);
        if (rule.rule_type === "daily") {
          additionalShares = additionalShares.mul(30);
        } else if (rule.rule_type === "weekly") {
          additionalShares = additionalShares.mul(4);
        }
      } else if (rule.amount_krw) {
        let amount = toDecimal(rule.amount_krw);
        if (rule.rule_type === "daily") {
          amount = amount.mul(30);
        } else if (rule.rule_type === "weekly") {
          amount = amount.mul(4);
        }

        additionalShares =
          catalog.priceCurrency === "USD" ? amount.div(price.mul(exchangeRate)) : amount.div(price);
      }

      positions.set(ticker, (positions.get(ticker) ?? new Decimal(0)).plus(additionalShares));
    });

    let monthlyDividend = new Decimal(0);
    let portfolioValue = new Decimal(0);

    params.holdings.forEach((holding) => {
      const ticker = holding.asset.ticker;
      const shares = positions.get(ticker) ?? new Decimal(0);
      const basePrice = toDecimal(assetCatalog[ticker]?.currentPrice ?? 0);
      const grownPrice = basePrice.mul(new Decimal(1).plus(growthRate).pow(index / 12));
      const assumption = params.assumptions.find((item) => item.asset_id === holding.asset_id && item.is_active);
      const baseAnnualDividendPerShare = assumptionTypeToAnnual({
        assumptionType: assumption?.assumption_type ?? "none",
        annualDividendPerShare: assumption?.annual_dividend_per_share ?? 0,
        monthlyDividendPerShare: assumption?.monthly_dividend_per_share ?? 0,
        weeklyDividendPerShare: assumption?.weekly_dividend_per_share ?? 0,
      });
      const annualPerShare = baseAnnualDividendPerShare.mul(new Decimal(1).plus(growthRate).pow(index / 12));

      portfolioValue = portfolioValue.plus(
        calculateCurrentValueKRW({
          shares,
          market: holding.asset.market,
          currentPrice: grownPrice,
          exchangeRate,
        }),
      );

      const annualDividend = holding.asset.market === "US" ? shares.mul(annualPerShare).mul(exchangeRate) : shares.mul(annualPerShare);

      monthlyDividend = monthlyDividend.plus(annualDividend.div(12));

      if (params.reinvest && monthlyDividend.gt(0)) {
        const reinvestShares =
          holding.asset.market === "US"
            ? annualDividend.div(12).div(grownPrice.mul(exchangeRate))
            : annualDividend.div(12).div(grownPrice);
        positions.set(ticker, shares.plus(reinvestShares.div(params.holdings.length || 1)));
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
    return {
      yearLabel: `${new Date().getFullYear() + yearIndex}년`,
      totalDividend: slice.reduce((acc, row) => acc.plus(row.expectedDividend), new Decimal(0)),
      monthlyAverage:
        slice.reduce((acc, row) => acc.plus(row.expectedDividend), new Decimal(0)).div(slice.length || 1),
    };
  });

  return {
    monthlyRows,
    yearlyTotals,
  };
}

export function sumCurrentPortfolioValue(holdings: HoldingWithAsset[], exchangeRate: Decimal.Value) {
  return holdings.reduce((acc, holding) => {
    const meta = assetCatalog[holding.asset.ticker];
    return acc.plus(
      calculateCurrentValueKRW({
        shares: holding.shares,
        market: holding.asset.market,
        currentPrice: meta?.currentPrice ?? 0,
        exchangeRate,
      }),
    );
  }, new Decimal(0));
}

export function sumMonthlyExpectedDividend(
  holdings: HoldingWithAsset[],
  assumptions: DividendAssumption[],
  exchangeRate: Decimal.Value,
) {
  // Expected dividends are calculated from the current holdings snapshot
  // and active assumptions only. Past actual dividends are not reverse-engineered.
  return holdings.reduce(
    (acc, holding) =>
      acc.plus(
        calculateMonthlyExpectedDividend({
          shares: holding.shares,
          asset: holding.asset,
          assumption: assumptions.find((item) => item.asset_id === holding.asset_id && item.is_active),
          exchangeRate,
        }),
      ),
    new Decimal(0),
  );
}

export function sumAnnualExpectedDividend(
  holdings: HoldingWithAsset[],
  assumptions: DividendAssumption[],
  exchangeRate: Decimal.Value,
) {
  // Expected annual dividends are forward-looking only.
  return holdings.reduce(
    (acc, holding) =>
      acc.plus(
        calculateAnnualExpectedDividend({
          shares: holding.shares,
          asset: holding.asset,
          assumption: assumptions.find((item) => item.asset_id === holding.asset_id && item.is_active),
          exchangeRate,
        }),
      ),
    new Decimal(0),
  );
}

export function findNextPayoutCountdown(holdings: HoldingWithAsset[]) {
  const now = new Date();
  const upcomingDates = holdings
    .filter((holding) => toDecimal(holding.shares).gt(0))
    .map((holding) => getNextDividendDate(holding.asset.dividend_frequency, now))
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
