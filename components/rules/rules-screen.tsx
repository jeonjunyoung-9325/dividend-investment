"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/page-header";
import { RulesPanel } from "@/components/rules/rules-panel";
import { getDashboardSnapshot } from "@/lib/queries";

export function RulesScreen() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboardSnapshot,
  });

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">투자 규칙을 불러오는 중입니다...</div>;
  }

  if (error || !data) {
    return <div className="text-sm text-red-600">투자 규칙을 불러오지 못했습니다.</div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Rules"
        title="자동 투자 패턴을 저장해 미래 배당을 계산합니다"
        description="금액 또는 주수 단위의 반복 투자 규칙을 만들어 projection 화면과 연결합니다."
      />
      <RulesPanel assets={data.holdings} rules={data.rules} />
    </div>
  );
}
