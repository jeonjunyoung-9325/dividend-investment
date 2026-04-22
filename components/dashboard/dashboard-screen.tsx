"use client";

import Decimal from "decimal.js";
import { BarChart3, CalendarClock, CircleDollarSign, Wallet, Waves } from "lucide-react";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { GoalCard } from "@/components/dashboard/goal-card";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { LiveDividendCounter } from "@/components/dashboard/live-dividend-counter";
import { MonthlyDividendChart, PortfolioDonutChart } from "@/components/dashboard/charts";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  calculateEffectiveHoldingValueKRW,
  calculateGoalProgress,
  getEffectiveExchangeRate,
  getEffectiveHoldingShares,
  calculateMonthlyExpectedDividend,
  calculatePortfolioWeights,
  findNextPayoutCountdown,
  groupActualDividendsByMonth,
  sumActualDividendsByMonth,
  sumActualDividendsByYear,
  sumAnnualExpectedDividend,
  sumCurrentPortfolioValue,
  sumMonthlyExpectedDividend,
} from "@/lib/calculations";
import { getDashboardSnapshot } from "@/lib/queries";
import { formatKRW, toDecimal } from "@/lib/utils";

const monthLabels = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"];

export function DashboardScreen() {
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboardSnapshot,
  });

  const derived = useMemo(() => {
    if (!data) {
      return null;
    }

    const exchangeRate = getEffectiveExchangeRate(
      data.fxRates,
      data.settings.exchange_rate,
      data.settings.auto_exchange_rate_enabled,
    );
    const totalValue = sumCurrentPortfolioValue(data.holdings, data.marketQuotes, exchangeRate, data.settings);
    const monthlyExpected = sumMonthlyExpectedDividend(data.holdings, data.assumptions, exchangeRate, data.settings);
    const annualExpected = sumAnnualExpectedDividend(data.holdings, data.assumptions, exchangeRate, data.settings);
    const monthlyActual = sumActualDividendsByMonth(data.actualDividends);
    const yearlyActual = sumActualDividendsByYear(data.actualDividends);

    const groupedActual = groupActualDividendsByMonth(data.actualDividends, selectedYear);
    const chartData = groupedActual.map(({ month, amount }) => {
      const expected = data.holdings.reduce((acc, holding) => {
        const monthly = calculateMonthlyExpectedDividend({
          shares: getEffectiveHoldingShares(holding, data.settings),
          asset: holding.asset,
          assumption: data.assumptions.find((item) => item.asset_id === holding.asset_id && item.is_active),
          exchangeRate,
          monthDate: new Date(selectedYear, month, 1),
        });
        return acc.plus(monthly);
      }, new Decimal(0));

      return {
        month: monthLabels[month],
        actual: amount.toNumber(),
        expected: expected.toNumber(),
      };
    });

    const donutData = calculatePortfolioWeights(
      data.holdings.map((holding) => {
        const value = calculateEffectiveHoldingValueKRW({
          holding,
          settings: data.settings,
          marketQuotes: data.marketQuotes,
          exchangeRate,
        });
        return {
          ticker: holding.asset.ticker,
          color: holding.asset.default_color,
          valueKRW: value,
        };
      }),
    ).map((item) => ({
      ticker: item.ticker,
      value: toDecimal(item.valueKRW).toNumber(),
      weight: item.weight.toNumber(),
      color: data.holdings.find((holding) => holding.asset.ticker === item.ticker)?.asset.default_color ?? "#94a3b8",
    }));

    const goal = calculateGoalProgress({
      goal: data.goals[0],
      monthlyExpectedDividendKRW: monthlyExpected,
      rules: data.rules,
      assumptions: data.assumptions,
      exchangeRate,
      marketQuotes: data.marketQuotes,
    });

    return {
      totalValue,
      monthlyExpected,
      annualExpected,
      monthlyActual,
      yearlyActual,
      exchangeRate,
      chartData,
      donutData,
      nextPayout: findNextPayoutCountdown(data.holdings, data.assumptions),
      goal,
      counterAnimationEnabled: data.settings.counter_animation_enabled,
    };
  }, [data, selectedYear]);

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">대시보드 데이터를 불러오는 중입니다...</div>;
  }

  if (error || !data || !derived) {
    return <div className="text-sm text-red-600">대시보드 데이터를 불러오지 못했습니다. Supabase 환경변수를 확인해 주세요.</div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Dashboard"
        title="지금도 배당이 쌓이고 있습니다"
        description="총 평가금액, 실제 수령 배당, 그리고 현재 보유 수량 기준의 미래 예상 배당을 한 화면에서 확인합니다. 과거 실제 배당 대상 수량은 현재 수량으로 역산하지 않습니다."
        actions={<Badge variant="success">자동 환율 {formatKRW(derived.exchangeRate, { withSuffix: false, maximumFractionDigits: 2 })}</Badge>}
      />

      <div className="grid gap-4 xl:grid-cols-6">
        <KpiCard label="총 평가금액" value={formatKRW(derived.totalValue)} helper="보유 종목의 현재 평가금액 합계" icon={<Wallet className="h-4 w-4" />} />
        <KpiCard label="이번 달 예상 배당" value={formatKRW(derived.monthlyExpected)} helper="현재 보유 수량과 기준값으로 계산한 미래 예상 배당" icon={<CircleDollarSign className="h-4 w-4" />} />
        <KpiCard label="이번 달 실제 수령" value={formatKRW(derived.monthlyActual)} helper="사용자가 직접 기록한 원화 기준 세전 입금액" icon={<Waves className="h-4 w-4" />} />
        <KpiCard label="올해 누적 실제 배당" value={formatKRW(derived.yearlyActual)} helper="실제 기록 합계이며 현재 수량으로 과거를 복원하지 않습니다" icon={<BarChart3 className="h-4 w-4" />} />
        <KpiCard label="올해 예상 총 배당" value={formatKRW(derived.annualExpected)} helper="현재 보유 수량과 dividend assumptions 기준 예상치" icon={<CircleDollarSign className="h-4 w-4" />} />
        <KpiCard
          label="다음 배당일까지"
          value={derived.nextPayout?.label ?? "예정 없음"}
          helper={derived.nextPayout ? `예상 지급일 ${derived.nextPayout.date.toLocaleDateString("ko-KR")}` : "보유 수량이 있는 배당 자산이 없습니다."}
          icon={<CalendarClock className="h-4 w-4" />}
        />
      </div>

      <LiveDividendCounter
        monthlyExpectedDividendKRW={derived.monthlyExpected.toFixed(2)}
        animationEnabled={derived.counterAnimationEnabled}
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
        <div className="space-y-6">
          <div className="flex items-center gap-2">
            {[selectedYear - 1, selectedYear, selectedYear + 1].map((year) => (
              <button
                key={year}
                className={`rounded-full px-4 py-2 text-sm font-semibold ${selectedYear === year ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}
                onClick={() => setSelectedYear(year)}
              >
                {year}년
              </button>
            ))}
          </div>
          <MonthlyDividendChart data={derived.chartData} />
        </div>
        <PortfolioDonutChart data={derived.donutData} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)]">
        <GoalCard
          progress={derived.goal.progress.toNumber()}
          current={formatKRW(derived.monthlyExpected)}
          goal={formatKRW(derived.goal.goalAmount)}
          monthlyGrowth={formatKRW(derived.goal.monthlyGrowth)}
          arrivalLabel={derived.goal.estimatedArrival ? derived.goal.estimatedArrival.toLocaleDateString("ko-KR") : "계산 불가"}
        />
        <Card>
          <CardContent className="grid gap-4 p-6 md:grid-cols-2">
            <div className="rounded-3xl bg-muted p-5">
              <p className="text-sm text-muted-foreground">이번 달 예상 배당 밀도</p>
              <p className="mt-3 text-2xl font-semibold">{formatKRW(derived.monthlyExpected.div(30))}</p>
              <p className="mt-2 text-sm text-muted-foreground">하루 평균 기준으로 보면 이 정도 속도로 배당이 쌓이는 셈입니다.</p>
            </div>
            <div className="rounded-3xl bg-accent p-5">
              <p className="text-sm text-muted-foreground">다음 확장 포인트</p>
              <p className="mt-3 text-lg font-semibold">예상 배당 기준값은 테이블로 분리되어 있습니다.</p>
              <p className="mt-2 text-sm text-muted-foreground">실제 배당은 입력 데이터, 예상 배당은 dividend assumptions로 완전히 분리되어 계산됩니다.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
