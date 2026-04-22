"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { deleteInvestmentRule, upsertInvestmentRule } from "@/lib/queries";
import { formatKRW } from "@/lib/utils";
import { HoldingWithAsset, RuleWithAsset } from "@/types";

const weekdays = ["일", "월", "화", "수", "목", "금", "토"];

export function RulesPanel({ assets, rules }: { assets: HoldingWithAsset[]; rules: RuleWithAsset[] }) {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [assetId, setAssetId] = useState(assets[0]?.asset_id ?? "");
  const [ruleType, setRuleType] = useState("monthly");
  const [amount, setAmount] = useState("");
  const [shares, setShares] = useState("");
  const [weekday, setWeekday] = useState("1");
  const [enabled, setEnabled] = useState(true);

  const saveMutation = useMutation({
    mutationFn: () =>
      upsertInvestmentRule({
        id: editingId ?? undefined,
        asset_id: assetId,
        rule_type: ruleType,
        amount_krw: amount || null,
        shares: shares || null,
        weekday: ruleType === "weekly" ? Number(weekday) : null,
        enabled,
      }),
    onSuccess: () => {
      toast.success(editingId ? "투자 규칙을 수정했습니다." : "투자 규칙을 추가했습니다.");
      queryClient.invalidateQueries({ queryKey: ["rules"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      resetForm();
    },
    onError: () => toast.error("투자 규칙 저장에 실패했습니다."),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteInvestmentRule,
    onSuccess: () => {
      toast.success("투자 규칙을 삭제했습니다.");
      queryClient.invalidateQueries({ queryKey: ["rules"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: () => toast.error("투자 규칙 삭제에 실패했습니다."),
  });

  function resetForm() {
    setEditingId(null);
    setAssetId(assets[0]?.asset_id ?? "");
    setRuleType("monthly");
    setAmount("");
    setShares("");
    setWeekday("1");
    setEnabled(true);
  }

  function loadRule(rule: RuleWithAsset) {
    setEditingId(rule.id);
    setAssetId(rule.asset_id);
    setRuleType(rule.rule_type);
    setAmount(rule.amount_krw ?? "");
    setShares(rule.shares ?? "");
    setWeekday(String(rule.weekday ?? 1));
    setEnabled(rule.enabled);
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
      <Card>
        <CardHeader>
          <CardTitle>{editingId ? "규칙 수정" : "새 규칙 추가"}</CardTitle>
          <CardDescription>금액 기반 또는 주수 기반으로 반복 투자 규칙을 저장합니다.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>종목</Label>
            <Select value={assetId} onValueChange={setAssetId}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {assets.map((asset) => (
                  <SelectItem key={asset.asset_id} value={asset.asset_id}>
                    {asset.asset.ticker}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>주기</Label>
            <Select value={ruleType} onValueChange={setRuleType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">daily</SelectItem>
                <SelectItem value="weekly">weekly</SelectItem>
                <SelectItem value="monthly">monthly</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>금액(원)</Label>
            <Input value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="예: 200000" />
          </div>
          <div className="space-y-2">
            <Label>주수</Label>
            <Input value={shares} onChange={(event) => setShares(event.target.value)} placeholder="예: 1" />
          </div>
          {ruleType === "weekly" ? (
            <div className="space-y-2">
              <Label>요일</Label>
              <Select value={weekday} onValueChange={setWeekday}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {weekdays.map((label, index) => (
                    <SelectItem key={label} value={String(index)}>
                      {label}요일
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : null}
          <div className="flex items-center justify-between rounded-2xl bg-muted p-4">
            <div>
              <p className="font-medium">활성화</p>
              <p className="text-sm text-muted-foreground">projection에 바로 반영됩니다.</p>
            </div>
            <Switch checked={enabled} onCheckedChange={setEnabled} />
          </div>
          <div className="flex gap-2">
            <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              {editingId ? "수정 저장" : "규칙 추가"}
            </Button>
            {editingId ? (
              <Button variant="outline" onClick={resetForm}>
                취소
              </Button>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>저장된 투자 규칙</CardTitle>
          <CardDescription>활성화된 규칙은 미래 배당 추정 화면에 즉시 반영됩니다.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {rules.map((rule) => (
            <div key={rule.id} className="flex flex-col gap-3 rounded-2xl border border-border p-4 md:flex-row md:items-center md:justify-between">
              <div className="space-y-1">
                <p className="font-semibold">
                  {rule.asset.ticker} · {rule.rule_type}
                </p>
                <p className="text-sm text-muted-foreground">
                  {rule.amount_krw ? formatKRW(rule.amount_krw) : `${rule.shares}주`}
                  {rule.rule_type === "weekly" && rule.weekday !== null ? ` / ${weekdays[rule.weekday]}요일` : ""}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div className="rounded-full bg-muted px-3 py-1 text-xs font-semibold text-muted-foreground">
                  {rule.enabled ? "활성" : "비활성"}
                </div>
                <Button variant="outline" size="icon" onClick={() => loadRule(rule)}>
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="icon" onClick={() => deleteMutation.mutate(rule.id)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
