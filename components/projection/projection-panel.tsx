"use client";

import { useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { buildProjectionSchedule } from "@/lib/calculations";
import { formatKRW } from "@/lib/utils";
import { DividendAssumption, HoldingWithAsset, ProjectionScenario, RuleWithAsset } from "@/types";

export function ProjectionPanel({
  holdings,
  rules,
  assumptions,
  exchangeRate,
}: {
  holdings: HoldingWithAsset[];
  rules: RuleWithAsset[];
  assumptions: DividendAssumption[];
  exchangeRate: string;
}) {
  const [years, setYears] = useState("3");
  const [scenario, setScenario] = useState<ProjectionScenario>("base");
  const [reinvest, setReinvest] = useState(true);

  const projection = useMemo(
    () =>
      buildProjectionSchedule({
        holdings,
        rules,
        assumptions,
        exchangeRate,
        years: Number(years),
        scenario,
        reinvest,
      }),
    [assumptions, exchangeRate, holdings, reinvest, rules, scenario, years],
  );

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>시나리오 설정</CardTitle>
          <CardDescription>기간, 성장률 가정, 재투자 여부를 조합해 미래 배당 흐름을 추정합니다.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
          <div className="space-y-2">
            <p className="text-sm font-medium">기간</p>
            <Select value={years} onValueChange={setYears}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">1년</SelectItem>
                <SelectItem value="3">3년</SelectItem>
                <SelectItem value="5">5년</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">시나리오</p>
            <Select value={scenario} onValueChange={(value) => setScenario(value as ProjectionScenario)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="conservative">보수적</SelectItem>
                <SelectItem value="base">기준</SelectItem>
                <SelectItem value="optimistic">낙관</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-between rounded-2xl border border-border bg-muted p-4 md:col-span-2">
            <div>
              <p className="font-medium">배당 재투자</p>
              <p className="text-sm text-muted-foreground">월별 예상 배당을 다시 편입해 성장 흐름을 반영합니다.</p>
            </div>
            <Switch checked={reinvest} onCheckedChange={setReinvest} />
          </div>
          <p className="text-sm leading-6 text-muted-foreground md:col-span-4">
            실제 배당 기록은 참고용으로만 분리 보관합니다. 이 projection은 현재 보유 수량과 투자 규칙으로 미래 보유 수량을 추정해 계산하며, 현재 수량으로 과거 ex-date 수량을 복원하지 않습니다.
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        {projection.yearlyTotals.map((row) => (
          <Card key={row.yearLabel}>
            <CardHeader>
              <CardTitle>{row.yearLabel}</CardTitle>
              <CardDescription>연도별 합계와 월평균입니다.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded-2xl bg-muted p-4">
                <p className="text-sm text-muted-foreground">연간 예상 배당</p>
                <p className="mt-2 text-2xl font-semibold">{formatKRW(row.totalDividend)}</p>
              </div>
              <div className="rounded-2xl bg-accent p-4">
                <p className="text-sm text-muted-foreground">월평균</p>
                <p className="mt-2 text-xl font-semibold">{formatKRW(row.monthlyAverage)}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>월별 예정표</CardTitle>
          <CardDescription>앞으로의 월별 예상 배당과 포트폴리오 평가금액 추정을 확인합니다.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="px-3 py-3 font-medium text-muted-foreground">월</th>
                <th className="px-3 py-3 font-medium text-muted-foreground">예상 배당</th>
                <th className="px-3 py-3 font-medium text-muted-foreground">평가금액</th>
              </tr>
            </thead>
            <tbody>
              {projection.monthlyRows.map((row) => (
                <tr key={row.monthLabel} className="border-b border-border/70">
                  <td className="px-3 py-3">{row.monthLabel}</td>
                  <td className="px-3 py-3">{formatKRW(row.expectedDividend)}</td>
                  <td className="px-3 py-3">{formatKRW(row.portfolioValue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
