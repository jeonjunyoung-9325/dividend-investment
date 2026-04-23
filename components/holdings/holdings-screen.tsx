"use client";

import Decimal from "decimal.js";
import { useQuery } from "@tanstack/react-query";
import { HoldingCard } from "@/components/holdings/holding-card";
import { PageHeader } from "@/components/layout/page-header";
import { getEffectiveExchangeRate } from "@/lib/calculations";
import { getDashboardSnapshot } from "@/lib/queries";
import { toDecimal } from "@/lib/utils";

export function HoldingsScreen() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboardSnapshot,
  });

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">보유 종목 데이터를 불러오는 중입니다...</div>;
  }

  if (error || !data) {
    return <div className="text-sm text-red-600">보유 종목 데이터를 불러오지 못했습니다.</div>;
  }

  const actualTotals = new Map<string, Decimal>();
  data.actualDividends.forEach((dividend) => {
    actualTotals.set(
      dividend.asset_id,
      (actualTotals.get(dividend.asset_id) ?? new Decimal(0)).plus(toDecimal(dividend.gross_amount_krw)),
    );
  });
  const exchangeRate = getEffectiveExchangeRate(
    data.fxRates,
    data.settings.exchange_rate,
    data.settings.auto_exchange_rate_enabled,
  );

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Holdings"
        title="보유 종목과 평가금액을 한국투자 API 기준으로 확인합니다"
        description="수동 보유 수량 입력은 제거했습니다. 보유 수량, 평단가, 평가금액, 현재가는 한국투자 Open API 동기화 결과를 기준으로 표시됩니다."
      />
      <div className="grid gap-6">
        {data.holdings.map((holding) => (
          <HoldingCard
            key={holding.asset_id}
            holding={holding}
            exchangeRate={exchangeRate.toString()}
            actualDividendTotal={(actualTotals.get(holding.asset_id) ?? new Decimal(0)).toFixed(2)}
            assumption={data.assumptions.find((item) => item.asset_id === holding.asset_id && item.is_active)}
            settings={data.settings}
            marketQuotes={data.marketQuotes}
          />
        ))}
      </div>
    </div>
  );
}
