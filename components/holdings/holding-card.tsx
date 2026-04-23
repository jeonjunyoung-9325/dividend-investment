"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  calculateAnnualExpectedDividend,
  calculateEffectiveHoldingValueKRW,
  getEffectiveHoldingAverageCostKRW,
  getEffectiveHoldingShares,
  getLatestQuoteForAsset,
} from "@/lib/calculations";
import { formatKRW, formatRelativeTimeFromNow, formatShares } from "@/lib/utils";
import { AppSettings, DividendAssumption, HoldingWithAsset, MarketQuote } from "@/types";

export function HoldingCard({
  holding,
  exchangeRate,
  actualDividendTotal,
  assumption,
  settings,
  marketQuotes,
}: {
  holding: HoldingWithAsset;
  exchangeRate: string;
  actualDividendTotal: string;
  assumption?: DividendAssumption;
  settings: AppSettings;
  marketQuotes: MarketQuote[];
}) {
  const quote = getLatestQuoteForAsset(holding.asset, marketQuotes);
  const effectiveShares = getEffectiveHoldingShares(holding, settings);
  const averageCost = getEffectiveHoldingAverageCostKRW(holding, settings);
  const currentValue = calculateEffectiveHoldingValueKRW({
    holding,
    settings,
    marketQuotes,
    exchangeRate,
  });
  const annualDividend = calculateAnnualExpectedDividend({
    shares: effectiveShares,
    asset: holding.asset,
    assumption,
    exchangeRate,
  });

  return (
    <Card className="overflow-hidden">
      <CardContent className="space-y-5 p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xl font-semibold">{holding.asset.name}</h3>
              <Badge variant="accent">{holding.asset.ticker}</Badge>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge variant="outline">{holding.asset.market}</Badge>
              <Badge variant="success">{holding.asset.asset_type}</Badge>
              <Badge variant="outline">{holding.asset.dividend_frequency}</Badge>
            </div>
          </div>
          <div
            className="h-12 w-12 rounded-2xl"
            style={{
              backgroundColor: `${holding.asset.default_color}22`,
              border: `1px solid ${holding.asset.default_color}55`,
            }}
          />
        </div>

        <div className="grid gap-3 md:grid-cols-4">
          <div className="rounded-2xl bg-muted p-4">
            <p className="text-sm text-muted-foreground">API 보유 수량</p>
            <p className="mt-2 text-lg font-semibold">{formatShares(effectiveShares)}주</p>
            <p className="mt-1 text-xs text-muted-foreground">한국투자 Open API 기준</p>
          </div>
          <div className="rounded-2xl bg-muted p-4">
            <p className="text-sm text-muted-foreground">평균 매입 단가</p>
            <p className="mt-2 text-lg font-semibold">{averageCost ? formatKRW(averageCost) : "-"}</p>
            <p className="mt-1 text-xs text-muted-foreground">API 응답 기준 원화 환산 평단가</p>
          </div>
          <div className="rounded-2xl bg-muted p-4">
            <p className="text-sm text-muted-foreground">평가금액</p>
            <p className="mt-2 text-lg font-semibold">{formatKRW(currentValue)}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              현재가 {quote ? `${quote.price} ${quote.currency}` : "없음"} · 소스 {quote?.provider ?? "미동기화"}
            </p>
          </div>
          <div className="rounded-2xl bg-muted p-4">
            <p className="text-sm text-muted-foreground">예상 연간 배당</p>
            <p className="mt-2 text-lg font-semibold">{formatKRW(annualDividend)}</p>
            <p className="mt-1 text-xs text-muted-foreground">기준값 방식 {assumption?.assumption_type ?? "none"}</p>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl bg-muted p-4">
            <p className="text-sm text-muted-foreground">실제 수령 누적</p>
            <p className="mt-2 text-lg font-semibold">{formatKRW(actualDividendTotal)}</p>
            <p className="mt-1 text-xs text-muted-foreground">실제 배당은 원화 기준 세전 입금액 수동 기록</p>
          </div>
          <div className="rounded-2xl bg-muted p-4">
            <p className="text-sm text-muted-foreground">동기화 상태</p>
            <p className="mt-2 text-lg font-semibold">{holding.last_synced_at ? "API 반영 완료" : "미동기화"}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {holding.last_synced_at ? `마지막 동기화 ${formatRelativeTimeFromNow(holding.last_synced_at)}` : "설정 화면에서 한국투자 잔고 동기화를 실행해 주세요."}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
