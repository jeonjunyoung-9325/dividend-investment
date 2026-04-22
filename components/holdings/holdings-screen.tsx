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
        title="보유 수량만 바꾸면 전체 대시보드가 즉시 따라옵니다"
        description="모든 종목은 고정 리스트로 제공됩니다. 소수점 투자까지 지원하며, 이 화면에서 사용자는 보유 수량만 편하게 수정하면 됩니다."
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
