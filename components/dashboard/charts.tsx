"use client";

import { Pie, PieChart, ResponsiveContainer, Cell, Tooltip, BarChart, Bar, CartesianGrid, XAxis, YAxis, Legend } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatKRW } from "@/lib/utils";

export function PortfolioDonutChart({
  data,
}: {
  data: { ticker: string; value: number; color: string; weight: number }[];
}) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>포트폴리오 비중</CardTitle>
        <CardDescription>현재 평가금액 기준 종목별 비중입니다.</CardDescription>
      </CardHeader>
      <CardContent className="h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="ticker" innerRadius={80} outerRadius={120} paddingAngle={3}>
              {data.map((entry) => (
                <Cell key={entry.ticker} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => formatKRW(Number(value ?? 0))} />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function MonthlyDividendChart({
  data,
}: {
  data: { month: string; actual: number; expected: number }[];
}) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>월별 배당 추이</CardTitle>
        <CardDescription>실제 수령과 예상 배당을 한 화면에서 비교합니다.</CardDescription>
      </CardHeader>
      <CardContent className="h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="month" tickLine={false} axisLine={false} />
            <YAxis tickFormatter={(value) => formatKRW(value, { withSuffix: false })} tickLine={false} axisLine={false} />
            <Tooltip formatter={(value) => formatKRW(Number(value ?? 0))} />
            <Legend />
            <Bar dataKey="actual" fill="var(--chart-1)" name="실제 배당" radius={[8, 8, 0, 0]} />
            <Bar dataKey="expected" fill="var(--chart-2)" name="예상 배당" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
