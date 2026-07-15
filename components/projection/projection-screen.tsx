"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/page-header";
import { ProjectionPanel } from "@/components/projection/projection-panel";
import { Card, CardContent } from "@/components/ui/card";
import {
  getEffectiveExchangeRate,
  sumActualDividendsByMonth,
  sumActualDividendsByYear,
} from "@/lib/calculations";
import { getDividendForecastSnapshot } from "@/lib/queries";
import { formatKRW } from "@/lib/utils";

export function ProjectionScreen() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dividend-forecast"],
    queryFn: getDividendForecastSnapshot,
  });

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">미래 배당 추정을 계산하는 중입니다...</div>;
  }

  if (error || !data) {
    return <div className="text-sm text-red-600">미래 배당 추정을 불러오지 못했습니다.</div>;
  }

  const monthlyActual = sumActualDividendsByMonth(data.actualDividends);
  const yearlyActual = sumActualDividendsByYear(data.actualDividends);
  const exchangeRate = getEffectiveExchangeRate(
    data.fxRates,
    data.settings.exchange_rate,
    data.settings.auto_exchange_rate_enabled,
  );

  return (
    <div className="space-y-5 sm:space-y-6">
      <PageHeader
        eyebrow="배당 예측"
        title="월별·연도별 예상 배당"
        description="실제 보유 수량, 매월 투자 규칙, JEPQ 배당 재투자를 함께 반영해 보수·기준·긍정 시나리오를 비교합니다."
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">이번 달 실제 수령 배당</p>
            <p className="mt-2 font-mono text-2xl font-semibold">{formatKRW(monthlyActual)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">올해 누적 실제 배당</p>
            <p className="mt-2 font-mono text-2xl font-semibold">{formatKRW(yearlyActual)}</p>
          </CardContent>
        </Card>
      </div>
      <ProjectionPanel
        holdings={data.holdings}
        rules={data.rules}
        assumptions={data.assumptions}
        marketQuotes={data.marketQuotes}
        settings={data.settings}
        exchangeRate={exchangeRate.toString()}
      />
    </div>
  );
}
