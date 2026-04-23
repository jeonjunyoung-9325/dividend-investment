"use client";

import Decimal from "decimal.js";
import { Pie, PieChart, ResponsiveContainer, Cell, Tooltip, BarChart, Bar, CartesianGrid, XAxis, YAxis } from "recharts";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getDashboardSnapshot, syncActualDividendRecords } from "@/lib/queries";
import { formatKRW, toDecimal } from "@/lib/utils";

const monthLabels = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"];

export function DividendsScreen() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboardSnapshot,
  });

  const syncMutation = useMutation({
    mutationFn: syncActualDividendRecords,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">배당 기록을 불러오는 중입니다...</div>;
  }

  if (error || !data) {
    return <div className="text-sm text-red-600">배당 기록을 불러오지 못했습니다.</div>;
  }

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
    data.actualDividends.reduce((map, row) => {
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
        return paidDate.getFullYear() === currentYear && paidDate.getMonth() === month;
      })
      .reduce((acc, row) => acc.plus(toDecimal(row.gross_amount_krw)), new Decimal(0));

    return {
      month: monthLabels[month],
      amount: total.toNumber(),
    };
  });

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Dividends"
        title="실제 수령 배당 기록을 API 기준으로 불러옵니다"
        description="테스트 값은 제거했고, 국내 실제 배당은 한국투자 계좌 권리현황 기준으로 자동 동기화합니다. 해외 실제 배당은 KIS가 계좌별 원화 세전 입금 row를 제공하지 않아 이번 버전에서는 제외합니다."
        actions={
          <Button onClick={() => syncMutation.mutate()} disabled={syncMutation.isPending}>
            실수령 배당 동기화
          </Button>
        }
      />

      {syncMutation.data?.note ? (
        <Card>
          <CardContent className="p-4 text-sm text-muted-foreground">{syncMutation.data.note}</CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
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
        <Card>
          <CardContent className="p-6">
            <p className="text-sm text-muted-foreground">기록 수</p>
            <p className="mt-3 text-3xl font-semibold">{data.actualDividends.length}건</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>월별 실제 배당 차트</CardTitle>
            <CardDescription>{currentYear}년 기준 API 동기화된 실제 입금 금액입니다.</CardDescription>
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
            <CardDescription>자동 동기화된 실제 현금흐름 기준입니다.</CardDescription>
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
          <CardDescription>국내 KIS 권리현황 기준 자동 동기화 목록입니다. 금액은 모두 원화 기준 세전 금액으로 표시합니다.</CardDescription>
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
              {data.actualDividends.map((row) => (
                <tr key={row.id} className="border-b border-border/70">
                  <td className="px-3 py-3">{new Date(row.paid_date).toLocaleDateString("ko-KR")}</td>
                  <td className="px-3 py-3">{row.asset.ticker}</td>
                  <td className="px-3 py-3">{formatKRW(row.gross_amount_krw)}</td>
                  <td className="px-3 py-3">{row.tax_amount_krw ? formatKRW(row.tax_amount_krw) : "-"}</td>
                  <td className="px-3 py-3">{row.source === "kis_domestic_period_rights" ? "KIS 국내 권리현황" : "수동"}</td>
                  <td className="px-3 py-3 text-muted-foreground">{row.memo || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.actualDividends.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              아직 자동 동기화된 실제 배당 기록이 없습니다. 실수령 배당 동기화를 눌러 국내 KIS 배당 기록을 불러와 주세요.
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
