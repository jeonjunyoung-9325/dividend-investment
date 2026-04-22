"use client";

import Decimal from "decimal.js";
import { LoaderCircle, RefreshCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { assetCatalog } from "@/lib/catalog/assets";
import { calculateAnnualExpectedDividend, calculateCurrentValueKRW } from "@/lib/calculations";
import { upsertHoldingShares } from "@/lib/queries";
import { formatKRW, formatRelativeTimeFromNow, formatShares, toDecimal } from "@/lib/utils";
import { DividendAssumption, HoldingWithAsset } from "@/types";

export function HoldingCard({
  holding,
  exchangeRate,
  actualDividendTotal,
  assumption,
}: {
  holding: HoldingWithAsset;
  exchangeRate: string;
  actualDividendTotal: string;
  assumption?: DividendAssumption;
}) {
  const [value, setValue] = useState(holding.shares);
  const queryClient = useQueryClient();
  const meta = assetCatalog[holding.asset.ticker];

  const currentValue = useMemo(
    () =>
      calculateCurrentValueKRW({
        shares: value,
        market: holding.asset.market,
        currentPrice: meta?.currentPrice ?? 0,
        exchangeRate,
      }),
    [exchangeRate, holding.asset.market, meta?.currentPrice, value],
  );

  const annualDividend = useMemo(
    () =>
      calculateAnnualExpectedDividend({
        shares: value,
        asset: holding.asset,
        assumption,
        exchangeRate,
      }),
    [assumption, exchangeRate, holding.asset, value],
  );

  const mutation = useMutation({
    mutationFn: async (nextShares: string) => upsertHoldingShares(holding.asset_id, nextShares),
    onMutate: async (nextShares) => {
      await queryClient.cancelQueries({ queryKey: ["holdings"] });
      const previous = queryClient.getQueryData<HoldingWithAsset[]>(["holdings"]);
      if (previous) {
        queryClient.setQueryData<HoldingWithAsset[]>(
          ["holdings"],
          previous.map((row) =>
            row.asset_id === holding.asset_id
              ? {
                  ...row,
                  shares: nextShares,
                  updated_at: new Date().toISOString(),
                }
              : row,
          ),
        );
      }
      return { previous };
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["holdings"], context.previous);
      }
      toast.error(`${holding.asset.ticker} 수량 저장에 실패했습니다.`);
    },
    onSuccess: () => {
      toast.success(`${holding.asset.ticker} 보유 수량을 저장했습니다.`);
      queryClient.invalidateQueries({ queryKey: ["holdings"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  function applyDelta(delta: string) {
    const nextValue = Decimal.max(toDecimal(value).plus(delta), 0);
    const normalized = nextValue.toFixed(8).replace(/\.?0+$/, "");
    setValue(normalized || "0");
  }

  function handleSave() {
    try {
      const decimal = toDecimal(value);
      if (decimal.lt(0)) {
        toast.error("보유 수량은 음수가 될 수 없습니다.");
        return;
      }

      const parts = value.split(".");
      if (parts[1] && parts[1].length > 8) {
        toast.error("보유 수량은 소수점 8자리까지 입력할 수 있습니다.");
        return;
      }

      mutation.mutate(decimal.toFixed(decimal.decimalPlaces() ?? 0));
    } catch {
      toast.error("올바른 수량 형식으로 입력해 주세요.");
    }
  }

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

        <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto]">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">현재 보유 수량</p>
            <Input value={value} onChange={(event) => setValue(event.target.value)} inputMode="decimal" />
            <p className="text-xs text-muted-foreground">최대 소수점 8자리까지 입력 가능합니다.</p>
          </div>
          <div className="grid grid-cols-2 gap-2 md:w-[164px]">
            {["+1", "-1", "+0.1", "-0.1"].map((delta) => (
              <Button
                key={delta}
                variant="outline"
                size="sm"
                onClick={() => applyDelta(delta)}
                className="rounded-xl"
              >
                {delta}
              </Button>
            ))}
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl bg-muted p-4">
            <p className="text-sm text-muted-foreground">평가금액</p>
            <p className="mt-2 text-lg font-semibold">{formatKRW(currentValue)}</p>
          </div>
          <div className="rounded-2xl bg-muted p-4">
            <p className="text-sm text-muted-foreground">예상 연간 배당</p>
            <p className="mt-2 text-lg font-semibold">{formatKRW(annualDividend)}</p>
            <p className="mt-1 text-xs text-muted-foreground">기준값 방식 {assumption?.assumption_type ?? "none"}</p>
          </div>
          <div className="rounded-2xl bg-muted p-4">
            <p className="text-sm text-muted-foreground">실제 수령 누적</p>
            <p className="mt-2 text-lg font-semibold">{formatKRW(actualDividendTotal)}</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">
            현재 표시 수량 {formatShares(value)}주 · 마지막 업데이트 {formatRelativeTimeFromNow(holding.updated_at)}
          </p>
          <Button onClick={handleSave} disabled={mutation.isPending}>
            {mutation.isPending ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCcw className="mr-2 h-4 w-4" />}
            수량 저장
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
