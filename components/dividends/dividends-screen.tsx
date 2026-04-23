"use client";

import Decimal from "decimal.js";
import { useEffect, useState } from "react";
import { Pie, PieChart, ResponsiveContainer, Cell, Tooltip, BarChart, Bar, CartesianGrid, XAxis, YAxis } from "recharts";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { fetchOverseasDividendReference, getDashboardSnapshot, syncActualDividendRecords } from "@/lib/queries";
import { formatKRW, toDecimal } from "@/lib/utils";

const monthLabels = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"];

const syncProgressStages = [
  { afterSeconds: 0, label: "동기화 요청을 시작하고 있습니다.", progress: 12 },
  { afterSeconds: 4, label: "국내 배당 권리현황을 조회하고 있습니다.", progress: 28 },
  { afterSeconds: 12, label: "해외 배당 권리 이력을 조회하고 있습니다.", progress: 52 },
  { afterSeconds: 24, label: "과거 보유 수량과 환율을 결합하고 있습니다.", progress: 74 },
  { afterSeconds: 40, label: "불러온 배당 기록을 저장하고 있습니다.", progress: 90 },
] as const;

function formatCompactDate(value: string) {
  if (!value || value.length !== 8) {
    return value || "-";
  }

  return `${value.slice(0, 4)}.${value.slice(4, 6)}.${value.slice(6, 8)}`;
}

export function DividendsScreen() {
  const queryClient = useQueryClient();
  const [syncElapsedSeconds, setSyncElapsedSeconds] = useState(0);
  const [selectedYear, setSelectedYear] = useState<string>("");
  const [selectedMonth, setSelectedMonth] = useState<string>("all");
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboardSnapshot,
  });

  const syncMutation = useMutation({
    mutationFn: syncActualDividendRecords,
    onMutate: () => {
      setSyncElapsedSeconds(0);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const overseasReferenceMutation = useMutation({
    mutationFn: fetchOverseasDividendReference,
  });

  useEffect(() => {
    if (!syncMutation.isPending) {
      return;
    }

    const intervalId = window.setInterval(() => {
      setSyncElapsedSeconds((current) => current + 1);
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [syncMutation.isPending]);

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">배당 기록을 불러오는 중입니다...</div>;
  }

  if (error || !data) {
    return <div className="text-sm text-red-600">배당 기록을 불러오지 못했습니다.</div>;
  }

  const availableYears = Array.from(
    new Set(data.actualDividends.map((row) => new Date(row.paid_date).getFullYear()).filter((value) => !Number.isNaN(value))),
  ).sort((left, right) => right - left);
  const resolvedYear = selectedYear || String(availableYears[0] ?? new Date().getFullYear());
  const filteredDividends = data.actualDividends.filter((row) => {
    const paidDate = new Date(row.paid_date);
    const matchesYear = String(paidDate.getFullYear()) === resolvedYear;
    const matchesMonth = selectedMonth === "all" || String(paidDate.getMonth() + 1) === selectedMonth;
    return matchesYear && matchesMonth;
  });

  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth();
  const monthTotal = data.actualDividends
    .filter((row) => {
      const paidDate = new Date(row.paid_date);
      return paidDate.getFullYear() === currentYear && paidDate.getMonth() === currentMonth;
    })
    .reduce((acc, row) => acc.plus(toDecimal(row.gross_amount_krw)), new Decimal(0));
  const yearTotal = data.actualDividends
    .filter((row) => new Date(row.paid_date).getFullYear() === currentYear)
    .reduce((acc, row) => acc.plus(toDecimal(row.gross_amount_krw)), new Decimal(0));

  const byTicker = Array.from(
    filteredDividends.reduce((map, row) => {
      const current = map.get(row.asset.ticker) ?? new Decimal(0);
      map.set(row.asset.ticker, current.plus(toDecimal(row.gross_amount_krw)));
      return map;
    }, new Map<string, Decimal>()),
  ).map(([ticker, amount]) => ({
    ticker,
    amount: amount.toNumber(),
    color: data.holdings.find((holding) => holding.asset.ticker === ticker)?.asset.default_color ?? "#94a3b8",
  }));

  const monthlyActuals = Array.from({ length: 12 }, (_, month) => {
    const total = data.actualDividends
      .filter((row) => {
        const paidDate = new Date(row.paid_date);
        return String(paidDate.getFullYear()) === resolvedYear && paidDate.getMonth() === month;
      })
      .reduce((acc, row) => acc.plus(toDecimal(row.gross_amount_krw)), new Decimal(0));

    return {
      month: monthLabels[month],
      amount: total.toNumber(),
    };
  });
  const filteredTotal = filteredDividends.reduce((acc, row) => acc.plus(toDecimal(row.gross_amount_krw)), new Decimal(0));
  const importedTickers = Array.from(new Set(data.actualDividends.map((row) => row.asset.ticker))).sort();
  const missingDividendTickers = data.holdings
    .filter((holding) => !importedTickers.includes(holding.asset.ticker) && holding.asset.ticker !== "IAU")
    .map((holding) => holding.asset.ticker);
  const currentSyncStage = syncProgressStages.reduce((selected, stage) => {
    if (syncElapsedSeconds >= stage.afterSeconds) {
      return stage;
    }
    return selected;
  }, syncProgressStages[0]);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Dividends"
        title="실제 수령 배당 기록을 API 기준으로 불러옵니다"
        description="테스트 값은 제거했고, 국내는 한국투자 계좌 권리현황 기준으로, 해외는 권리조회와 기준일 결제잔고를 결합해 과거 기준수량 기반 실제 배당을 원화 기준으로 동기화합니다."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => overseasReferenceMutation.mutate()} disabled={overseasReferenceMutation.isPending}>
              해외 배당 참고 불러오기
            </Button>
            <Button onClick={() => syncMutation.mutate()} disabled={syncMutation.isPending}>
              {syncMutation.isPending ? `실수령 배당 동기화 중 · ${syncElapsedSeconds}초` : "실수령 배당 동기화"}
            </Button>
          </div>
        }
      />

      {syncMutation.isPending ? (
        <Card>
          <CardHeader>
            <CardTitle>실수령 배당 동기화 진행 중</CardTitle>
            <CardDescription>한국투자 API 조회량에 따라 10초 이상 걸릴 수 있습니다. 화면을 닫지 말고 잠시 기다려 주세요.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>{currentSyncStage.label}</span>
                <span className="text-muted-foreground">{syncElapsedSeconds}초 경과</span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div
                  className="h-2 rounded-full bg-[var(--chart-3)] transition-all duration-500"
                  style={{ width: `${currentSyncStage.progress}%` }}
                />
              </div>
            </div>
            <div className="grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
              <div>1. 국내 배당 권리현황 조회</div>
              <div>2. 해외 배당 권리이력 조회</div>
              <div>3. 과거 보유 수량/환율 결합</div>
              <div>4. 실제 배당 기록 저장</div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {syncMutation.error ? (
        <Card className="border-red-200">
          <CardContent className="p-4 text-sm text-red-600">
            {syncMutation.error instanceof Error ? syncMutation.error.message : "실수령 배당 동기화에 실패했습니다."}
          </CardContent>
        </Card>
      ) : null}

      {syncMutation.data?.note ? (
        <Card>
          <CardContent className="p-4 text-sm text-muted-foreground">{syncMutation.data.note}</CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>연도 / 월 기준으로 보기</CardTitle>
          <CardDescription>실제 배당 기록 목록과 종목별 비중은 선택한 연도와 월 기준으로 필터링됩니다.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-[minmax(0,220px)_minmax(0,220px)_1fr]">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">연도</p>
            <Select value={resolvedYear} onValueChange={setSelectedYear}>
              <SelectTrigger>
                <SelectValue placeholder="연도 선택" />
              </SelectTrigger>
              <SelectContent>
                {availableYears.map((year) => (
                  <SelectItem key={year} value={String(year)}>
                    {year}년
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">월</p>
            <Select value={selectedMonth} onValueChange={setSelectedMonth}>
              <SelectTrigger>
                <SelectValue placeholder="월 선택" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">전체 월</SelectItem>
                {monthLabels.map((label, index) => (
                  <SelectItem key={label} value={String(index + 1)}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="rounded-2xl border border-border/70 bg-muted/40 p-4 text-sm text-muted-foreground">
            반영된 실제 배당 종목: {importedTickers.length > 0 ? importedTickers.join(", ") : "없음"}
            <div className="mt-2">
              아직 배당 기록이 없는 보유 종목: {missingDividendTickers.length > 0 ? missingDividendTickers.join(", ") : "없음"}
            </div>
          </div>
        </CardContent>
      </Card>

      {overseasReferenceMutation.data ? (
        <Card>
          <CardHeader>
            <CardTitle>해외 배당 참고 내역</CardTitle>
            <CardDescription>{overseasReferenceMutation.data.note}</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-left text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-3 py-3 font-medium text-muted-foreground">종목</th>
                  <th className="px-3 py-3 font-medium text-muted-foreground">현지 기준일</th>
                  <th className="px-3 py-3 font-medium text-muted-foreground">확정 여부</th>
                  <th className="px-3 py-3 font-medium text-muted-foreground">주당 배당</th>
                  <th className="px-3 py-3 font-medium text-muted-foreground">현재 보유 수량</th>
                  <th className="px-3 py-3 font-medium text-muted-foreground">현재 보유 기준 참고 환산액</th>
                </tr>
              </thead>
              <tbody>
                {overseasReferenceMutation.data.events.map((row) => (
                  <tr key={`${row.ticker}-${row.localRecordDate}-${row.perShareAmount}`} className="border-b border-border/70">
                    <td className="px-3 py-3">
                      {row.ticker}
                      <div className="text-xs text-muted-foreground">{row.name}</div>
                    </td>
                    <td className="px-3 py-3">
                      {formatCompactDate(row.localRecordDate || row.baseDate)}
                    </td>
                    <td className="px-3 py-3">{row.status || "-"}</td>
                    <td className="px-3 py-3">
                      {row.perShareAmount} {row.currency}
                    </td>
                    <td className="px-3 py-3">{row.currentShares}주</td>
                    <td className="px-3 py-3">
                      {row.estimatedAmountKrw ? formatKRW(row.estimatedAmountKrw) : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {overseasReferenceMutation.data.events.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                현재 해외 보유 종목 기준으로 조회된 금액 포함 배당 권리 내역이 없습니다. KIS가 일정 row만 주고 금액을 0으로 내려주는 경우에는 표에 표시하지 않습니다.
              </div>
            ) : null}
            <p className="mt-4 text-xs text-muted-foreground">
              참고 환산액은 현재 보유 수량 기준이며 실제 과거 실수령액과 다를 수 있습니다.
            </p>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="p-6">
            <p className="text-sm text-muted-foreground">
              {resolvedYear}년 {selectedMonth === "all" ? "전체" : `${selectedMonth}월`} 실제 세전 배당
            </p>
            <p className="mt-3 text-3xl font-semibold">{formatKRW(filteredTotal)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <p className="text-sm text-muted-foreground">이번 달 실제 세전 배당</p>
            <p className="mt-3 text-3xl font-semibold">{formatKRW(monthTotal)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <p className="text-sm text-muted-foreground">올해 누적 실제 세전 배당</p>
            <p className="mt-3 text-3xl font-semibold">{formatKRW(yearTotal)}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>월별 실제 배당 차트</CardTitle>
            <CardDescription>{resolvedYear}년 기준 API 동기화된 실제 입금 금액입니다.</CardDescription>
          </CardHeader>
          <CardContent className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={monthlyActuals}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="month" tickLine={false} axisLine={false} />
                <YAxis tickFormatter={(value) => formatKRW(value, { withSuffix: false })} tickLine={false} axisLine={false} />
                <Tooltip formatter={(value) => formatKRW(Number(value ?? 0))} />
                <Bar dataKey="amount" fill="var(--chart-3)" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>종목별 실제 배당 비중</CardTitle>
            <CardDescription>{resolvedYear}년 {selectedMonth === "all" ? "전체 월" : `${selectedMonth}월`} 기준입니다.</CardDescription>
          </CardHeader>
          <CardContent className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={byTicker} dataKey="amount" nameKey="ticker" innerRadius={70} outerRadius={110}>
                  {byTicker.map((entry) => (
                    <Cell key={entry.ticker} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => formatKRW(Number(value ?? 0))} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>배당 기록 목록</CardTitle>
          <CardDescription>국내/해외 KIS 자동 동기화 목록입니다. 금액은 모두 원화 기준 세전 금액으로 표시합니다.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[880px] text-left text-sm">
              <thead>
                <tr className="border-b border-border">
                <th className="px-3 py-3 font-medium text-muted-foreground">입금일</th>
                <th className="px-3 py-3 font-medium text-muted-foreground">종목</th>
                <th className="px-3 py-3 font-medium text-muted-foreground">세전 금액</th>
                <th className="px-3 py-3 font-medium text-muted-foreground">세금</th>
                <th className="px-3 py-3 font-medium text-muted-foreground">출처</th>
                <th className="px-3 py-3 font-medium text-muted-foreground">메모</th>
              </tr>
            </thead>
              <tbody>
              {filteredDividends.map((row) => (
                <tr key={row.id} className="border-b border-border/70">
                  <td className="px-3 py-3">{new Date(row.paid_date).toLocaleDateString("ko-KR")}</td>
                  <td className="px-3 py-3">{row.asset.ticker}</td>
                  <td className="px-3 py-3">{formatKRW(row.gross_amount_krw)}</td>
                  <td className="px-3 py-3">{row.tax_amount_krw ? formatKRW(row.tax_amount_krw) : "-"}</td>
                  <td className="px-3 py-3">
                    {row.source === "kis_domestic_period_rights"
                      ? "KIS 국내 권리현황"
                      : row.source === "kis_overseas_rights_balance"
                        ? "KIS 해외 권리+기준잔고"
                        : "수동"}
                  </td>
                  <td className="px-3 py-3 text-muted-foreground">{row.memo || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredDividends.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              선택한 연도와 월에 해당하는 실제 배당 기록이 없습니다. 다른 기간을 선택하거나 실수령 배당 동기화를 다시 실행해 주세요.
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
