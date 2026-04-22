"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { createActualDividend, updateActualDividend } from "@/lib/queries";
import { toDecimal } from "@/lib/utils";
import { DividendWithAsset, HoldingWithAsset } from "@/types";

export function DividendForm({
  assets,
  editing,
  onComplete,
}: {
  assets: HoldingWithAsset[];
  editing?: DividendWithAsset | null;
  onComplete?: () => void;
}) {
  const queryClient = useQueryClient();
  const [assetId, setAssetId] = useState(editing?.asset_id ?? assets[0]?.asset_id ?? "");
  const [paidDate, setPaidDate] = useState(editing?.paid_date ?? new Date().toISOString().slice(0, 10));
  const [amount, setAmount] = useState(editing?.gross_amount_krw ?? "");
  const [memo, setMemo] = useState(editing?.memo ?? "");

  const mutation = useMutation({
    mutationFn: async () => {
      const payload = {
        asset_id: assetId,
        paid_date: paidDate,
        gross_amount_krw: toDecimal(amount).toFixed(2),
        memo,
      };
      return editing ? updateActualDividend(editing.id, payload) : createActualDividend(payload);
    },
    onSuccess: () => {
      toast.success(editing ? "배당 기록을 수정했습니다." : "배당 기록을 추가했습니다.");
      queryClient.invalidateQueries({ queryKey: ["dividends"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      if (!editing) {
        setAmount("");
        setMemo("");
      }
      onComplete?.();
    },
    onError: () => {
      toast.error("배당 기록 저장에 실패했습니다.");
    },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!assetId || !amount || toDecimal(amount).lt(0)) {
      toast.error("종목과 금액을 올바르게 입력해 주세요.");
      return;
    }
    mutation.mutate();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{editing ? "배당 기록 수정" : "실제 배당 기록 추가"}</CardTitle>
        <CardDescription>원화 기준 세전 배당금을 기록합니다. 모든 금액 표시는 원화 형식으로 통일됩니다.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label>입금일</Label>
            <Input type="date" value={paidDate} onChange={(event) => setPaidDate(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>종목</Label>
            <Select value={assetId} onValueChange={setAssetId}>
              <SelectTrigger>
                <SelectValue placeholder="종목 선택" />
              </SelectTrigger>
              <SelectContent>
                {assets.map((asset) => (
                  <SelectItem key={asset.asset_id} value={asset.asset_id}>
                    {asset.asset.ticker} · {asset.asset.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>금액(원)</Label>
            <Input
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              placeholder="예: 60000"
              inputMode="decimal"
            />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label>메모</Label>
            <Textarea value={memo} onChange={(event) => setMemo(event.target.value)} placeholder="분배금 메모" />
          </div>
          <div className="md:col-span-2">
            <Button type="submit" disabled={mutation.isPending}>
              {editing ? "수정 저장" : "기록 추가"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
