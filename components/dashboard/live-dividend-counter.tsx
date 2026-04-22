"use client";

import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { calculateLiveDividendCounter } from "@/lib/calculations";
import { formatKRW } from "@/lib/utils";

export function LiveDividendCounter({
  monthlyExpectedDividendKRW,
  animationEnabled,
}: {
  monthlyExpectedDividendKRW: string;
  animationEnabled: boolean;
}) {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const interval = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  const counter = useMemo(
    () =>
      calculateLiveDividendCounter({
        monthlyExpectedDividendKRW,
        now,
        animationEnabled,
      }),
    [animationEnabled, monthlyExpectedDividendKRW, now],
  );

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>실시간 배당 카운터</CardTitle>
        <CardDescription>이번 달 예상 배당을 월 전체에 균등 분배해 지금 쌓인 흐름으로 보여줍니다.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-8">
        {animationEnabled ? (
          <motion.div
            key={counter.accumulated.toFixed(2)}
            initial={{ opacity: 0.5, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
          >
            <p className="text-sm text-muted-foreground">지금 쌓인 배당</p>
            <p className="currency-glow mt-2 text-4xl font-semibold tracking-tight text-primary">
              {formatKRW(counter.accumulated, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </motion.div>
        ) : (
          <div>
            <p className="text-sm text-muted-foreground">지금 쌓인 배당</p>
            <p className="currency-glow mt-2 text-4xl font-semibold tracking-tight text-primary">
              {formatKRW(counter.accumulated, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
        )}

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl bg-muted p-4">
            <p className="text-sm text-muted-foreground">하루당</p>
            <p className="mt-2 text-lg font-semibold">{formatKRW(counter.dailyRate)}</p>
          </div>
          <div className="rounded-2xl bg-muted p-4">
            <p className="text-sm text-muted-foreground">시간당</p>
            <p className="mt-2 text-lg font-semibold">
              {formatKRW(counter.hourlyRate, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
          <div className="rounded-2xl bg-muted p-4">
            <p className="text-sm text-muted-foreground">분당</p>
            <p className="mt-2 text-lg font-semibold">
              {formatKRW(counter.minutelyRate, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
