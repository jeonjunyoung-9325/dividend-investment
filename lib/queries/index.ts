"use client";

import { getSupabaseBrowserClient } from "@/lib/supabase/client";
import {
  ActualDividend,
  AppSettings,
  Asset,
  DashboardSnapshot,
  DividendAssumption,
  FxRate,
  Goal,
  Holding,
  HoldingWithAsset,
  InvestmentRule,
  MarketQuote,
  RuleWithAsset,
} from "@/types";

function requireSingle<T>(value: T | null, message: string) {
  if (!value) {
    throw new Error(message);
  }
  return value;
}

async function parseJsonResponse<T>(response: Response, fallbackMessage: string): Promise<T> {
  const text = await response.text();

  if (!text) {
    if (!response.ok) {
      throw new Error(fallbackMessage);
    }
    return {} as T;
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    if (!response.ok) {
      throw new Error(text.slice(0, 160) || fallbackMessage);
    }
    throw new Error(fallbackMessage);
  }
}

export async function listAssets() {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase.from("assets").select("*").order("display_order");
  if (error) throw error;
  return (data ?? []) as Asset[];
}

export async function listHoldings() {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase.from("holdings").select("*").order("updated_at", { ascending: false });
  if (error) throw error;
  return (data ?? []) as Holding[];
}

export async function listActualDividends() {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase.from("actual_dividends").select("*").order("paid_date", { ascending: false });
  if (error) throw error;
  return (data ?? []) as ActualDividend[];
}

export async function listInvestmentRules() {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase.from("investment_rules").select("*").order("created_at");
  if (error) throw error;
  return (data ?? []) as InvestmentRule[];
}

export async function listGoals() {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase.from("goals").select("*").order("created_at");
  if (error) throw error;
  return (data ?? []) as Goal[];
}

export async function listDividendAssumptions() {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase
    .from("dividend_assumptions")
    .select("*")
    .order("updated_at", { ascending: false });
  if (error) throw error;
  return (data ?? []) as DividendAssumption[];
}

export async function listMarketQuotes() {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase.from("market_quotes").select("*").order("fetched_at", { ascending: false });
  if (error) throw error;
  return (data ?? []) as MarketQuote[];
}

export async function listFxRates() {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase.from("fx_rates").select("*").order("fetched_at", { ascending: false });
  if (error) throw error;
  return (data ?? []) as FxRate[];
}

export async function getAppSettings() {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase.from("app_settings").select("*").limit(1).maybeSingle();
  if (error) throw error;
  return requireSingle(data as AppSettings | null, "app_settings 기본 레코드를 찾을 수 없습니다.");
}

export async function listHoldingsWithAssets(): Promise<HoldingWithAsset[]> {
  const [assets, holdings] = await Promise.all([listAssets(), listHoldings()]);
  const assetMap = new Map(assets.map((asset) => [asset.id, asset]));

  return holdings
    .map((holding) => ({
      ...holding,
      asset: requireSingle(assetMap.get(holding.asset_id), `asset ${holding.asset_id} not found`),
    }))
    .sort((a, b) => a.asset.display_order - b.asset.display_order);
}

export async function listRulesWithAssets(): Promise<RuleWithAsset[]> {
  const [assets, rules] = await Promise.all([listAssets(), listInvestmentRules()]);
  const assetMap = new Map(assets.map((asset) => [asset.id, asset]));

  return rules.map((rule) => ({
    ...rule,
    asset: requireSingle(assetMap.get(rule.asset_id), `asset ${rule.asset_id} not found`),
  }));
}

export async function listDividendRowsWithAssets() {
  const [assets, dividends] = await Promise.all([listAssets(), listActualDividends()]);
  const assetMap = new Map(assets.map((asset) => [asset.id, asset]));

  return dividends.map((dividend) => ({
    ...dividend,
    asset: requireSingle(assetMap.get(dividend.asset_id), `asset ${dividend.asset_id} not found`),
  }));
}

export async function getDashboardSnapshot(): Promise<DashboardSnapshot> {
  const [assets, holdings, actualDividends, rules, goals, settings, assumptions, marketQuotes, fxRates] = await Promise.all([
    listAssets(),
    listHoldingsWithAssets(),
    listDividendRowsWithAssets(),
    listRulesWithAssets(),
    listGoals(),
    getAppSettings(),
    listDividendAssumptions(),
    listMarketQuotes(),
    listFxRates(),
  ]);

  return {
    assets,
    holdings,
    actualDividends,
    rules,
    goals,
    settings,
    assumptions,
    marketQuotes,
    fxRates,
  };
}

export async function upsertHoldingShares(assetId: string, shares: string) {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase
    .from("holdings")
    .upsert(
      {
        asset_id: assetId,
        shares,
        updated_at: new Date().toISOString(),
      },
      { onConflict: "asset_id" },
    )
    .select("*")
    .single();

  if (error) throw error;
  return data as Holding;
}

export async function createActualDividend(input: {
  asset_id: string;
  paid_date: string;
  gross_amount_krw: string;
  memo?: string;
}) {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase
    .from("actual_dividends")
    .insert({
      ...input,
      memo: input.memo?.trim() || null,
    })
    .select("*")
    .single();
  if (error) throw error;
  return data as ActualDividend;
}

export async function updateActualDividend(
  id: string,
  input: {
    asset_id: string;
    paid_date: string;
    gross_amount_krw: string;
    memo?: string;
  },
) {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase
    .from("actual_dividends")
    .update({
      ...input,
      memo: input.memo?.trim() || null,
      updated_at: new Date().toISOString(),
    })
    .eq("id", id)
    .select("*")
    .single();
  if (error) throw error;
  return data as ActualDividend;
}

export async function deleteActualDividend(id: string) {
  const supabase = getSupabaseBrowserClient();
  const { error } = await supabase.from("actual_dividends").delete().eq("id", id);
  if (error) throw error;
  return id;
}

export async function upsertInvestmentRule(input: {
  id?: string;
  asset_id: string;
  rule_type: string;
  amount_krw: string | null;
  shares: string | null;
  weekday: number | null;
  enabled: boolean;
}) {
  const supabase = getSupabaseBrowserClient();
  const payload = {
    ...input,
    updated_at: new Date().toISOString(),
  };

  const query = input.id
    ? supabase.from("investment_rules").update(payload).eq("id", input.id)
    : supabase.from("investment_rules").insert(payload);

  const { data, error } = await query.select("*").single();
  if (error) throw error;
  return data as InvestmentRule;
}

export async function deleteInvestmentRule(id: string) {
  const supabase = getSupabaseBrowserClient();
  const { error } = await supabase.from("investment_rules").delete().eq("id", id);
  if (error) throw error;
  return id;
}

export async function updateAppSettings(input: Partial<AppSettings>) {
  const settings = await getAppSettings();
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase
    .from("app_settings")
    .update({
      ...input,
      updated_at: new Date().toISOString(),
    })
    .eq("id", settings.id)
    .select("*")
    .single();

  if (error) throw error;
  return data as AppSettings;
}

export async function upsertGoal(input: { id?: string; label: string; target_amount_krw: string }) {
  const supabase = getSupabaseBrowserClient();

  const query = input.id
    ? supabase
        .from("goals")
        .update({
          ...input,
          updated_at: new Date().toISOString(),
        })
        .eq("id", input.id)
    : supabase.from("goals").insert(input);

  const { data, error } = await query.select("*").single();
  if (error) throw error;
  return data as Goal;
}

export async function upsertDividendAssumption(input: {
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
}) {
  const supabase = getSupabaseBrowserClient();
  const payload = {
    ...input,
    source_note: input.source_note?.trim() || null,
  };

  const query = input.id
    ? supabase.from("dividend_assumptions").update(payload).eq("id", input.id)
    : supabase.from("dividend_assumptions").insert(payload);

  const { data, error } = await query.select("*").single();
  if (error) throw error;
  return data as DividendAssumption;
}

export async function refreshMarketQuotes() {
  const response = await fetch("/api/market/refresh", {
    method: "POST",
  });

  const json = await parseJsonResponse<{
    message?: string;
    quotesRefreshed?: number;
    fxProvider?: string;
    kisConfigured?: boolean;
  }>(response, "시세 갱신 응답을 읽지 못했습니다.");
  if (!response.ok) {
    throw new Error(json.message ?? "시세 갱신에 실패했습니다.");
  }

  if (!json.kisConfigured) {
    throw new Error("Vercel 또는 로컬 환경에 한국투자 Open API 환경변수가 설정되지 않았습니다.");
  }

  return json;
}

export async function syncBrokerageAccount() {
  const response = await fetch("/api/brokerage/sync", {
    method: "POST",
  });

  const json = await parseJsonResponse<{
    message?: string;
    reason?: string;
    skipped?: boolean;
    holdingsUpdated?: number;
  }>(response, "증권사 동기화 응답을 읽지 못했습니다.");
  if (!response.ok) {
    throw new Error(json.message ?? "증권사 동기화에 실패했습니다.");
  }

  if (json.skipped) {
    throw new Error(json.reason ?? "한국투자 Open API 환경설정을 확인해 주세요.");
  }

  return json;
}

export async function syncActualDividendRecords() {
  const response = await fetch("/api/dividends/sync", {
    method: "POST",
  });

  const json = await parseJsonResponse<{
    message?: string;
    importedCount?: number;
    note?: string;
  }>(response, "실제 배당 동기화 응답을 읽지 못했습니다.");

  if (!response.ok) {
    throw new Error(json.message ?? "실제 배당 동기화에 실패했습니다.");
  }

  return json;
}

export async function fetchOverseasDividendReference() {
  const response = await fetch("/api/dividends/overseas-reference", {
    method: "POST",
  });

  const json = await parseJsonResponse<{
    message?: string;
    note?: string;
    events?: Array<{
      ticker: string;
      name: string;
      baseDate: string;
      localRecordDate: string;
      status: string;
      perShareAmount: string;
      currency: string;
      currentShares: string;
      estimatedAmountKrw: string | null;
    }>;
  }>(response, "해외 배당 참고 응답을 읽지 못했습니다.");

  if (!response.ok) {
    throw new Error(json.message ?? "해외 배당 참고 데이터를 불러오지 못했습니다.");
  }

  return {
    note: json.note ?? "",
    events: json.events ?? [],
  };
}
