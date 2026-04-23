"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/page-header";
import { SettingsPanel } from "@/components/settings/settings-panel";
import { getDashboardSnapshot } from "@/lib/queries";

export function SettingsScreen() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboardSnapshot,
  });

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">설정을 불러오는 중입니다...</div>;
  }

  if (error || !data) {
    return <div className="text-sm text-red-600">설정을 불러오지 못했습니다.</div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Settings"
        title="앱 기본값과 목표를 관리합니다"
        description="한국투자 Open API 동기화 상태와 예상 배당 기준값, 목표 금액을 한 곳에서 관리합니다."
      />
      <SettingsPanel
        settings={data.settings}
        goal={data.goals[0]}
        assets={data.holdings}
        assumptions={data.assumptions}
        fxRates={data.fxRates}
        marketQuotes={data.marketQuotes}
      />
    </div>
  );
}
