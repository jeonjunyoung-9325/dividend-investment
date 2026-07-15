"use client";

import { useMemo, useState } from "react";
import { ProjectionChart } from "@/components/projection/projection-chart";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { buildProjectionSchedule, projectionScenarioAssumptions } from "@/lib/calculations";
import { formatKRW, formatShares } from "@/lib/utils";
import type {
  AppSettings,
  DividendAssumption,
  HoldingWithAsset,
  MarketQuote,
  ProjectionScenario,
  RuleWithAsset,
} from "@/types";

const scenarioOrder: ProjectionScenario[] = ["conservative", "base", "optimistic"];
const scenarioStyles: Record<ProjectionScenario, string> = {
  conservative: "border-slate-300",
  base: "border-primary/50",
  optimistic: "border-orange-300",
};

function formatRate(rate: string) {
  return `${Number(rate) > 0 ? "+" : ""}${(Number(rate) * 100).toFixed(0)}%`;
}

function ruleFrequencyLabel(rule: RuleWithAsset) {
  if (rule.rule_type === "daily") return "평일마다";
  if (rule.rule_type === "weekly") return "매주";
  return "매월";
}

export function ProjectionPanel({
  holdings,
  rules,
  assumptions,
  marketQuotes,
  settings,
  exchangeRate,
}: {
  holdings: HoldingWithAsset[];
  rules: RuleWithAsset[];
  assumptions: DividendAssumption[];
  marketQuotes: MarketQuote[];
  settings: AppSettings;
  exchangeRate: string;
}) {
  const [years, setYears] = useState("1");
  const [reinvest, setReinvest] = useState(true);

  const projections = useMemo(
    () =>
      Object.fromEntries(
        scenarioOrder.map((scenario) => [
          scenario,
          buildProjectionSchedule({
            holdings,
            rules,
            assumptions,
            marketQuotes,
            settings,
            exchangeRate,
            years: Number(years),
            scenario,
            reinvest,
            reinvestTargetTicker: "JEPQ",
          }),
        ]),
      ) as Record<ProjectionScenario, ReturnType<typeof buildProjectionSchedule>>,
    [assumptions, exchangeRate, holdings, marketQuotes, reinvest, rules, settings, years],
  );

  const enabledRules = rules.filter((rule) => rule.enabled);
  const reinvestmentWarning = projections.base.reinvestmentWarning;

  return (
    <div className="space-y-4 sm:space-y-5">
      <Card>
        <CardContent className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
          <div className="min-w-0">
            <p className="font-semibold">예측 조건</p>
            <p className="mt-1 text-sm leading-5 text-muted-foreground">
              현재 보유 수량에 저장된 투자 규칙을 더하고, 세후 추정 배당은 매월 JEPQ에 재투자합니다.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <Select value={years} onValueChange={setYears}>
              <SelectTrigger aria-label="예측 기간" className="w-28">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">1년</SelectItem>
                <SelectItem value="3">3년</SelectItem>
                <SelectItem value="5">5년</SelectItem>
              </SelectContent>
            </Select>
            <label className="flex min-h-11 items-center gap-2 rounded-xl border border-border bg-white/80 px-3 text-sm">
              <Switch checked={reinvest} onCheckedChange={setReinvest} />
              JEPQ 재투자
            </label>
          </div>
        </CardContent>
      </Card>

      {reinvestmentWarning ? (
        <div className="rounded-2xl border border-amber-300 bg-warning px-4 py-3 text-sm text-warning-foreground">
          {reinvestmentWarning} JEPQ 종목을 동기화하면 자동으로 반영됩니다.
        </div>
      ) : null}

      <section aria-label="예상 배당 시나리오" className="grid grid-cols-3 gap-2 md:hidden">
        {scenarioOrder.map((scenario) => {
          const projection = projections[scenario];
          const total = projection.yearlyTotals[0]?.totalNetDividend ?? 0;
          return (
            <Card key={scenario} className={scenarioStyles[scenario]}>
              <CardContent className="p-3 text-center">
                <p className="text-xs font-semibold">{projection.scenario.label}</p>
                <p className="mt-2 font-mono text-base font-semibold">{Math.round(Number(total) / 10_000).toLocaleString("ko-KR")}만원</p>
                <p className="mt-1 text-[10px] text-muted-foreground">향후 12개월</p>
              </CardContent>
            </Card>
          );
        })}
      </section>

      <section aria-label="예상 배당 시나리오 상세" className="hidden gap-3 md:grid md:grid-cols-3">
        {scenarioOrder.map((scenario) => {
          const projection = projections[scenario];
          const firstYear = projection.yearlyTotals[0];
          const finalMonth = projection.monthlyRows.at(-1);
          const assumption = projectionScenarioAssumptions[scenario];

          return (
            <Card key={scenario} className={scenarioStyles[scenario]}>
              <CardContent className="p-5">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-semibold">{assumption.label} 시나리오</p>
                  <span className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">
                    배당 {formatRate(assumption.payoutGrowthRate)}
                  </span>
                </div>
                <p className="mt-5 text-xs text-muted-foreground">향후 12개월 예상 세후</p>
                <p className="mt-1 font-mono text-2xl font-semibold tracking-tight">
                  {formatKRW(firstYear?.totalNetDividend ?? 0)}
                </p>
                <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-sm">
                  <span className="text-muted-foreground">예측 마지막 달</span>
                  <strong>{formatKRW(finalMonth?.netDividend ?? 0)}</strong>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </section>

      <ProjectionChart projections={projections} />

      <Card>
        <CardContent className="p-0">
          <div className="border-b border-border px-5 py-4">
            <h3 className="font-semibold">연도별 예상 세후 배당</h3>
            <p className="mt-1 text-sm text-muted-foreground">월별 추정값을 연도 단위로 합산했습니다.</p>
          </div>
          <div className="grid gap-3 p-4 sm:hidden">
            {projections.base.yearlyTotals.map((row, index) => (
              <div key={row.yearLabel} className="rounded-xl border border-border bg-muted/40 p-3">
                <div className="flex items-center justify-between">
                  <strong>{row.yearLabel}</strong>
                  <span className="text-xs text-muted-foreground">투자 {formatKRW(row.totalRegularInvestment)}</span>
                </div>
                <dl className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                  <div><dt className="text-muted-foreground">보수</dt><dd className="mt-1 font-semibold">{Math.round(projections.conservative.yearlyTotals[index].totalNetDividend.toNumber() / 10_000).toLocaleString("ko-KR")}만원</dd></div>
                  <div><dt className="text-muted-foreground">기준</dt><dd className="mt-1 font-semibold text-primary">{Math.round(row.totalNetDividend.toNumber() / 10_000).toLocaleString("ko-KR")}만원</dd></div>
                  <div><dt className="text-muted-foreground">긍정</dt><dd className="mt-1 font-semibold">{Math.round(projections.optimistic.yearlyTotals[index].totalNetDividend.toNumber() / 10_000).toLocaleString("ko-KR")}만원</dd></div>
                </dl>
              </div>
            ))}
          </div>
          <div className="hidden overflow-x-auto sm:block">
            <table className="w-full min-w-[620px] text-left text-sm">
              <thead className="bg-muted/60 text-muted-foreground">
                <tr>
                  <th className="px-5 py-3 font-medium">연도</th>
                  <th className="px-5 py-3 font-medium">보수</th>
                  <th className="px-5 py-3 font-medium">기준</th>
                  <th className="px-5 py-3 font-medium">긍정</th>
                  <th className="px-5 py-3 font-medium">정기 투자금</th>
                </tr>
              </thead>
              <tbody>
                {projections.base.yearlyTotals.map((row, index) => (
                  <tr key={row.yearLabel} className="border-t border-border/70">
                    <td className="px-5 py-3 font-medium">{row.yearLabel}</td>
                    <td className="px-5 py-3">{formatKRW(projections.conservative.yearlyTotals[index].totalNetDividend)}</td>
                    <td className="px-5 py-3 font-semibold text-primary">{formatKRW(row.totalNetDividend)}</td>
                    <td className="px-5 py-3">{formatKRW(projections.optimistic.yearlyTotals[index].totalNetDividend)}</td>
                    <td className="px-5 py-3 text-muted-foreground">{formatKRW(row.totalRegularInvestment)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <details className="rounded-2xl border border-border bg-card px-4 py-3 text-sm">
        <summary className="cursor-pointer font-medium">계산 기준과 투자 규칙 보기</summary>
        <div className="mt-4 grid gap-5 border-t border-border pt-4 lg:grid-cols-2">
          <div>
            <p className="font-medium">시나리오 가정</p>
            <ul className="mt-2 space-y-1.5 text-muted-foreground">
              {scenarioOrder.map((scenario) => {
                const item = projectionScenarioAssumptions[scenario];
                return (
                  <li key={scenario}>
                    {item.label}: 주가 연 {formatRate(item.priceGrowthRate)}, 주당 배당 연 {formatRate(item.payoutGrowthRate)}
                  </li>
                );
              })}
              <li>예상 원천징수: 국내 15.4%, 해외 15% 단순 가정</li>
              <li>세후 추정 배당 전액을 매월 말 JEPQ 소수점 수량으로 재투자</li>
            </ul>
          </div>
          <div>
            <p className="font-medium">적용 중인 투자 규칙 {enabledRules.length}개</p>
            <ul className="mt-2 grid gap-1.5 text-muted-foreground sm:grid-cols-2">
              {enabledRules.map((rule) => (
                <li key={rule.id}>
                  {rule.asset.ticker} · {ruleFrequencyLabel(rule)} · {rule.amount_krw ? formatKRW(rule.amount_krw) : `${formatShares(rule.shares ?? 0)}주`}
                </li>
              ))}
            </ul>
          </div>
        </div>
        <p className="mt-4 text-xs leading-5 text-muted-foreground">
          추정치이며 실제 지급액과 다를 수 있습니다. 휴장일, 수수료, 환율 변동, 배당 정책 변경은 확정 전에는 알 수 없습니다.
        </p>
      </details>
    </div>
  );
}
