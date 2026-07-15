"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent } from "@/components/ui/card";
import { buildProjectionSchedule } from "@/lib/calculations";
import { formatKRW } from "@/lib/utils";
import type { ProjectionScenario } from "@/types";

type Projection = ReturnType<typeof buildProjectionSchedule>;

export function ProjectionChart({ projections }: { projections: Record<ProjectionScenario, Projection> }) {
  const data = projections.base.monthlyRows.map((row, index) => ({
    month: row.monthLabel.replace("년 ", ".").replace("월", ""),
    conservative: projections.conservative.monthlyRows[index].netDividend.toNumber(),
    base: row.netDividend.toNumber(),
    optimistic: projections.optimistic.monthlyRows[index].netDividend.toNumber(),
  }));

  return (
    <Card>
      <CardContent className="p-4 sm:p-5">
        <div className="mb-4">
          <h3 className="font-semibold">월별 예상 세후 배당</h3>
          <p className="mt-1 text-sm text-muted-foreground">정기 투자와 JEPQ 재투자를 포함한 월별 흐름입니다.</p>
        </div>
        <div className="h-[280px] w-full sm:h-[360px]">
          <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 720, height: 360 }}>
            <LineChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 5" vertical={false} />
              <XAxis dataKey="month" interval="preserveStartEnd" tick={{ fill: "var(--muted-foreground)", fontSize: 12 }} tickLine={false} axisLine={false} />
              <YAxis width={56} tickFormatter={(value: number) => `${Math.round(value / 10_000)}만`} tick={{ fill: "var(--muted-foreground)", fontSize: 12 }} tickLine={false} axisLine={false} />
              <Tooltip formatter={(value) => formatKRW(Number(value))} labelFormatter={(label) => `${label}`} />
              <Legend iconType="line" wrapperStyle={{ fontSize: 13 }} />
              <Line dataKey="conservative" name="보수" dot={false} isAnimationActive={false} stroke="#64748b" strokeWidth={2} type="monotone" />
              <Line dataKey="base" name="기준" dot={false} isAnimationActive={false} stroke="var(--chart-1)" strokeWidth={3} type="monotone" />
              <Line dataKey="optimistic" name="긍정" dot={false} isAnimationActive={false} stroke="var(--chart-3)" strokeWidth={2} type="monotone" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
