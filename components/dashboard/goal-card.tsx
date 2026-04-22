import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function GoalCard({
  progress,
  current,
  goal,
  monthlyGrowth,
  arrivalLabel,
}: {
  progress: number;
  current: string;
  goal: string;
  monthlyGrowth: string;
  arrivalLabel: string;
}) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>배당 목표 진행률</CardTitle>
        <CardDescription>지금 속도와 투자 규칙을 기준으로 목표에 얼마나 가까워졌는지 보여줍니다.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">현재 월 예상 배당</span>
            <span className="font-semibold">{current}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">목표</span>
            <span className="font-semibold">{goal}</span>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-muted">
            <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(progress, 100)}%` }} />
          </div>
          <p className="text-sm text-muted-foreground">{progress.toFixed(1)}% 달성</p>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl bg-accent p-4">
            <p className="text-sm text-muted-foreground">월 성장 여력</p>
            <p className="mt-2 text-lg font-semibold">{monthlyGrowth}</p>
          </div>
          <div className="rounded-2xl bg-warning p-4">
            <p className="text-sm text-muted-foreground">예상 도달 시점</p>
            <p className="mt-2 text-lg font-semibold">{arrivalLabel}</p>
          </div>
        </div>

        <p className="rounded-2xl border border-border bg-muted/40 p-4 text-sm leading-6 text-muted-foreground">
          오늘 입력한 수량과 규칙이 그대로 이어져도, 배당은 조용히 누적됩니다. 지금의 작은 흐름이 다음 현금흐름의 시작점입니다.
        </p>
      </CardContent>
    </Card>
  );
}
