"use client";

import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { refreshMarketQuotes, syncBrokerageAccount, updateAppSettings, upsertDividendAssumption, upsertGoal } from "@/lib/queries";
import { formatKRW, formatRelativeTimeFromNow } from "@/lib/utils";
import { AppSettings, DividendAssumption, FxRate, Goal, HoldingWithAsset, MarketQuote } from "@/types";

export function SettingsPanel({
  settings,
  goal,
  assets,
  assumptions,
  fxRates,
  marketQuotes,
}: {
  settings: AppSettings;
  goal?: Goal;
  assets: HoldingWithAsset[];
  assumptions: DividendAssumption[];
  fxRates: FxRate[];
  marketQuotes: MarketQuote[];
}) {
  const queryClient = useQueryClient();
  const [taxMode, setTaxMode] = useState(settings.tax_mode);
  const [counterAnimationEnabled, setCounterAnimationEnabled] = useState(settings.counter_animation_enabled);
  const [goalLabel, setGoalLabel] = useState(goal?.label ?? "월 배당 목표");
  const [goalAmount, setGoalAmount] = useState(goal?.target_amount_krw ?? "1000000");

  const latestFx = useMemo(
    () =>
      fxRates
        .filter((row) => row.pair === "USD/KRW")
        .sort((a, b) => new Date(b.fetched_at).getTime() - new Date(a.fetched_at).getTime())[0],
    [fxRates],
  );
  const latestQuoteAt = useMemo(
    () => [...marketQuotes].sort((a, b) => new Date(b.fetched_at).getTime() - new Date(a.fetched_at).getTime())[0]?.fetched_at,
    [marketQuotes],
  );

  const settingsMutation = useMutation({
    mutationFn: () =>
      updateAppSettings({
        tax_mode: taxMode,
        counter_animation_enabled: counterAnimationEnabled,
        auto_exchange_rate_enabled: true,
        auto_broker_sync_enabled: true,
      }),
    onSuccess: () => {
      toast.success("앱 표시 설정을 저장했습니다.");
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: () => toast.error("앱 설정 저장에 실패했습니다."),
  });

  const goalMutation = useMutation({
    mutationFn: () =>
      upsertGoal({
        id: goal?.id,
        label: goalLabel,
        target_amount_krw: goalAmount,
      }),
    onSuccess: () => {
      toast.success("목표를 저장했습니다.");
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: () => toast.error("목표 저장에 실패했습니다."),
  });

  const assumptionMutation = useMutation({
    mutationFn: upsertDividendAssumption,
    onSuccess: () => {
      toast.success("예상 배당 기준값을 저장했습니다.");
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: () => toast.error("예상 배당 기준값 저장에 실패했습니다."),
  });

  const marketRefreshMutation = useMutation({
    mutationFn: refreshMarketQuotes,
    onSuccess: (result) => {
      toast.success(`시세 ${result.quotesRefreshed}건과 환율을 갱신했습니다.`);
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "시세 갱신에 실패했습니다."),
  });

  const brokerageSyncMutation = useMutation({
    mutationFn: syncBrokerageAccount,
    onSuccess: (result) => {
      toast.success(`한국투자 잔고 ${result.holdingsUpdated}건을 동기화했습니다.`);
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "한국투자 계좌 동기화에 실패했습니다."),
  });

  function resetDefaults() {
    setTaxMode("gross");
    setCounterAnimationEnabled(true);
    setGoalLabel("월 배당 100만원");
    setGoalAmount("1000000");
  }

  return (
    <div className="grid gap-6">
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>API 동기화 설정</CardTitle>
            <CardDescription>보유 수량, 평단가, 평가금액, 현재가, 환율은 한국투자 Open API를 기준으로 사용합니다.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl bg-muted p-4">
                <p className="text-sm text-muted-foreground">현재 USD/KRW 환율</p>
                <p className="mt-2 text-lg font-semibold">
                  {latestFx ? formatKRW(latestFx.rate, { withSuffix: false, maximumFractionDigits: 4 }) : "미동기화"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {latestFx ? `${latestFx.provider} · ${formatRelativeTimeFromNow(latestFx.fetched_at)}` : "먼저 시세/환율 갱신을 실행해 주세요."}
                </p>
              </div>
              <div className="rounded-2xl bg-muted p-4">
                <p className="text-sm text-muted-foreground">현재가 캐시 상태</p>
                <p className="mt-2 text-lg font-semibold">{marketQuotes.length}개 종목</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {latestQuoteAt ? `마지막 갱신 ${formatRelativeTimeFromNow(latestQuoteAt)}` : "아직 시세 캐시가 없습니다."}
                </p>
              </div>
            </div>

            <div className="flex items-center justify-between rounded-2xl bg-muted p-4">
              <div>
                <p className="font-medium">포트폴리오 데이터 소스</p>
                <p className="text-sm text-muted-foreground">수동 입력은 더 이상 사용하지 않고, API 동기화값만 사용합니다.</p>
              </div>
              <span className="rounded-full bg-primary/10 px-3 py-1 text-sm font-semibold text-primary">API 전용</span>
            </div>

            <div className="space-y-2">
              <Label>세금 표시 모드</Label>
              <Select value={taxMode} onValueChange={setTaxMode}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gross">세전 보기</SelectItem>
                  <SelectItem value="net-ready">세후 추정 보기</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between rounded-2xl bg-muted p-4">
              <div>
                <p className="font-medium">카운터 애니메이션</p>
                <p className="text-sm text-muted-foreground">실시간 배당 카운터 애니메이션만 켜고 끕니다.</p>
              </div>
              <Switch checked={counterAnimationEnabled} onCheckedChange={setCounterAnimationEnabled} />
            </div>

            <div className="flex gap-2">
              <Button onClick={() => settingsMutation.mutate()}>표시 설정 저장</Button>
              <Button variant="outline" onClick={resetDefaults}>
                기본값 초기화
              </Button>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => marketRefreshMutation.mutate()} disabled={marketRefreshMutation.isPending}>
                시세/환율 즉시 갱신
              </Button>
              <Button variant="outline" onClick={() => brokerageSyncMutation.mutate()} disabled={brokerageSyncMutation.isPending}>
                한국투자 잔고 동기화
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>배당 목표</CardTitle>
            <CardDescription>동기부여 카드에 표시할 목표 라벨과 금액을 설정합니다.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>목표 이름</Label>
              <Input value={goalLabel} onChange={(event) => setGoalLabel(event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>목표 금액(원)</Label>
              <Input value={goalAmount} onChange={(event) => setGoalAmount(event.target.value)} />
            </div>
            <Button onClick={() => goalMutation.mutate()}>목표 저장</Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>예상 배당 기준값 관리</CardTitle>
          <CardDescription>
            실제 배당과 분리된 예상 배당 계산 엔진입니다. API는 잔고/가격/환율 자동화에만 쓰고, 예상 배당은 이 기준값 레이어로 별도 계산합니다.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {assets.map((asset) => {
            const assumption = assumptions.find((item) => item.asset_id === asset.asset_id);
            return <AssumptionRow key={asset.asset_id} asset={asset} assumption={assumption} onSave={assumptionMutation.mutate} />;
          })}
        </CardContent>
      </Card>
    </div>
  );
}

function AssumptionRow({
  asset,
  assumption,
  onSave,
}: {
  asset: HoldingWithAsset;
  assumption?: DividendAssumption;
  onSave: (input: {
    id?: string;
    asset_id: string;
    assumption_type: string;
    annual_dividend_per_share: string | null;
    quarterly_dividend_per_share: string | null;
    monthly_dividend_per_share: string | null;
    weekly_dividend_per_share: string | null;
    distribution_months: number[] | null;
    source_note: string | null;
    updated_at: string;
    is_active: boolean;
  }) => void;
}) {
  const [assumptionType, setAssumptionType] = useState(assumption?.assumption_type ?? "none");
  const [annualValue, setAnnualValue] = useState(assumption?.annual_dividend_per_share ?? "");
  const [quarterlyValue, setQuarterlyValue] = useState(assumption?.quarterly_dividend_per_share ?? "");
  const [monthlyValue, setMonthlyValue] = useState(assumption?.monthly_dividend_per_share ?? "");
  const [weeklyValue, setWeeklyValue] = useState(assumption?.weekly_dividend_per_share ?? "");
  const [distributionMonths, setDistributionMonths] = useState(assumption?.distribution_months?.join(",") ?? "3,6,9,12");
  const [sourceNote, setSourceNote] = useState(assumption?.source_note ?? "");
  const [updatedDate, setUpdatedDate] = useState((assumption?.updated_at ?? new Date().toISOString()).slice(0, 10));

  return (
    <div className="grid gap-4 rounded-3xl border border-border p-4 md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-[minmax(0,1.2fr)_180px_repeat(4,minmax(110px,1fr))_minmax(0,1fr)_minmax(0,1.2fr)_160px_auto]">
      <div className="md:col-span-2 xl:col-span-4 2xl:col-span-1">
        <p className="font-semibold">
          {asset.asset.ticker} · {asset.asset.name}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          방식 {assumptionType} · 마지막 업데이트 {new Date(`${updatedDate}T00:00:00`).toLocaleDateString("ko-KR")}
        </p>
      </div>
      <Select value={assumptionType} onValueChange={(value) => setAssumptionType(value as typeof assumptionType)}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="annual_per_share">연 배당/주</SelectItem>
          <SelectItem value="quarterly_per_share">분기 배당/주</SelectItem>
          <SelectItem value="monthly_per_share">월 배당/주</SelectItem>
          <SelectItem value="weekly_per_share">주 배당/주</SelectItem>
          <SelectItem value="none">배당 없음</SelectItem>
        </SelectContent>
      </Select>
      <Input value={annualValue} onChange={(event) => setAnnualValue(event.target.value)} placeholder="연 배당/주" />
      <Input value={quarterlyValue} onChange={(event) => setQuarterlyValue(event.target.value)} placeholder="분기 배당/주" />
      <Input value={monthlyValue} onChange={(event) => setMonthlyValue(event.target.value)} placeholder="월 배당/주" />
      <Input value={weeklyValue} onChange={(event) => setWeeklyValue(event.target.value)} placeholder="주 배당/주" />
      <Input value={distributionMonths} onChange={(event) => setDistributionMonths(event.target.value)} placeholder="지급월 예: 3,6,9,12" />
      <Input value={sourceNote} onChange={(event) => setSourceNote(event.target.value)} placeholder="기준 메모" />
      <Input type="date" value={updatedDate} onChange={(event) => setUpdatedDate(event.target.value)} />
      <Button
        onClick={() =>
          onSave({
            id: assumption?.id,
            asset_id: asset.asset_id,
            assumption_type: assumptionType,
            annual_dividend_per_share: annualValue || null,
            quarterly_dividend_per_share: quarterlyValue || null,
            monthly_dividend_per_share: monthlyValue || null,
            weekly_dividend_per_share: weeklyValue || null,
            distribution_months:
              assumptionType === "quarterly_per_share"
                ? distributionMonths
                    .split(",")
                    .map((value) => Number(value.trim()))
                    .filter((value) => Number.isInteger(value) && value >= 1 && value <= 12)
                : null,
            source_note: sourceNote || null,
            updated_at: new Date(`${updatedDate}T00:00:00`).toISOString(),
            is_active: assumptionType !== "none",
          })
        }
      >
        저장
      </Button>
    </div>
  );
}
