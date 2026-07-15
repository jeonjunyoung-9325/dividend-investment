import { NextResponse } from "next/server";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import type {
  ActualDividend,
  AppSettings,
  Asset,
  FxRate,
  Holding,
  HoldingWithAsset,
  DividendAssumption,
  InvestmentRule,
  MarketQuote,
  RuleWithAsset,
} from "@/types";

export const runtime = "nodejs";

const fallbackSettings: AppSettings = {
  id: "static-fallback",
  exchange_rate: "1365.5",
  tax_mode: "gross",
  counter_animation_enabled: false,
  auto_exchange_rate_enabled: false,
  auto_broker_sync_enabled: false,
  portfolio_data_source: "manual",
  created_at: "",
  updated_at: "",
};

function requireSingle<T>(value: T | null, message: string) {
  if (!value) {
    throw new Error(message);
  }
  return value;
}

function withTimeout<T>(promise: PromiseLike<T>, timeoutMs = 2500) {
  return new Promise<T>((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error("dividend forecast snapshot timed out")), timeoutMs);

    Promise.resolve(promise).then(
      (value) => {
        clearTimeout(timeout);
        resolve(value);
      },
      (error) => {
        clearTimeout(timeout);
        reject(error);
      },
    );
  });
}

export async function GET() {
  try {
    const supabase = getSupabaseServerClient();
    const [
      { data: assetsData, error: assetsError },
      { data: holdingsData, error: holdingsError },
      { data: settingsData, error: settingsError },
    ] = await withTimeout(
      Promise.all([
        supabase.from("assets").select("*").order("display_order"),
        supabase.from("holdings").select("*").order("updated_at", { ascending: false }),
        supabase.from("app_settings").select("*").limit(1).maybeSingle(),
      ]),
    );

    if (assetsError) throw assetsError;
    if (holdingsError) throw holdingsError;
    if (settingsError) throw settingsError;

    const assets = (assetsData ?? []) as Asset[];
    const assetMap = new Map(assets.map((asset) => [asset.id, asset]));
    const holdings = ((holdingsData ?? []) as Holding[])
      .map<HoldingWithAsset>((holding) => ({
        ...holding,
        asset: requireSingle(assetMap.get(holding.asset_id) ?? null, `asset ${holding.asset_id} not found`),
      }))
      .sort((a, b) => a.asset.display_order - b.asset.display_order);
    const settings = requireSingle(settingsData as AppSettings | null, "app_settings 기본 레코드를 찾을 수 없습니다.");

    const [
      { data: actualDividendsData },
      { data: marketQuotesData },
      { data: fxRatesData },
      { data: rulesData, error: rulesError },
      { data: assumptionsData, error: assumptionsError },
    ] = await withTimeout(
      Promise.all([
        supabase.from("actual_dividends").select("*").order("paid_date", { ascending: false }),
        supabase.from("market_quotes").select("*").order("fetched_at", { ascending: false }),
        supabase.from("fx_rates").select("*").order("fetched_at", { ascending: false }),
        supabase.from("investment_rules").select("*").order("created_at"),
        supabase.from("dividend_assumptions").select("*").order("updated_at", { ascending: false }),
      ]),
    );

    if (rulesError) throw rulesError;
    if (assumptionsError) throw assumptionsError;

    const actualDividends = ((actualDividendsData ?? []) as ActualDividend[])
      .map((dividend) => {
        const asset = assetMap.get(dividend.asset_id);
        return asset ? { ...dividend, asset } : null;
      })
      .filter((dividend): dividend is NonNullable<typeof dividend> => Boolean(dividend));
    const rules = ((rulesData ?? []) as InvestmentRule[]).map<RuleWithAsset>((rule) => ({
      ...rule,
      asset: requireSingle(assetMap.get(rule.asset_id) ?? null, `asset ${rule.asset_id} not found`),
    }));

    return NextResponse.json({
      holdings,
      settings,
      actualDividends,
      marketQuotes: (marketQuotesData ?? []) as MarketQuote[],
      fxRates: (fxRatesData ?? []) as FxRate[],
      rules,
      assumptions: (assumptionsData ?? []) as DividendAssumption[],
    });
  } catch (error) {
    console.error("dividend forecast snapshot failed", error);
    return NextResponse.json({
      holdings: [],
      settings: fallbackSettings,
      actualDividends: [],
      marketQuotes: [],
      fxRates: [],
      rules: [],
      assumptions: [],
      warning: "보유 수량 저장소에 연결하지 못해 정적 fallback 데이터를 표시합니다.",
    });
  }
}
