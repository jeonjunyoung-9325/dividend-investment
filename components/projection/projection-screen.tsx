"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/page-header";
import { ProjectionPanel } from "@/components/projection/projection-panel";
import { Card, CardContent } from "@/components/ui/card";
import {
  sumActualDividendsByMonth,
  sumActualDividendsByYear,
  sumAnnualExpectedDividend,
  sumMonthlyExpectedDividend,
} from "@/lib/calculations";
import { getDashboardSnapshot } from "@/lib/queries";
import { formatKRW } from "@/lib/utils";

export function ProjectionScreen() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboardSnapshot,
  });

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">미래 배당 추정을 계산하는 중입니다...</div>;
  }

  if (error || !data) {
    return <div className="text-sm text-red-600">미래 배당 추정을 불러오지 못했습니다.</div>;
  }

  const monthlyActual = sumActualDividendsByMonth(data.actualDividends);
  const yearlyActual = sumActualDividendsByYear(data.actualDividends);

  const monthlyExpected = sumMonthlyExpectedDividend(data.holdings, data.assumptions, data.settings.exchange_rate);
  const annualExpected = sumAnnualExpectedDividend(data.holdings, data.assumptions, data.settings.exchange_rate);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Projection"
        title="앞으로 배당이 얼마나 커질 수 있는지 살펴봅니다"
        description="미래 예상 배당은 현재 보유 수량과 반복 투자 규칙을 바탕으로 추정합니다. 과거 실제 배당은 사용자가 기록한 실수령 금액을 그대로 정답으로 사용합니다."
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <p className="text-sm text-muted-foreground">이번 달 실제 수령 배당</p>
            <p className="mt-3 text-2xl font-semibold">{formatKRW(monthlyActual)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <p className="text-sm text-muted-foreground">이번 달 예상 배당</p>
            <p className="mt-3 text-2xl font-semibold">{formatKRW(monthlyExpected)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <p className="text-sm text-muted-foreground">올해 누적 실제 배당</p>
            <p className="mt-3 text-2xl font-semibold">{formatKRW(yearlyActual)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <p className="text-sm text-muted-foreground">올해 예상 총 배당</p>
            <p className="mt-3 text-2xl font-semibold">{formatKRW(annualExpected)}</p>
          </CardContent>
        </Card>
      </div>
      <ProjectionPanel holdings={data.holdings} rules={data.rules} assumptions={data.assumptions} exchangeRate={data.settings.exchange_rate} />
    </div>
  );
}
