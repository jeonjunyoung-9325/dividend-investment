export type Market = "US" | "KR";
export type AssetType = "core" | "income" | "satellite" | "hedge";
export type DividendFrequency = "weekly" | "monthly" | "quarterly" | "none";
export type RuleType = "daily" | "weekly" | "monthly";
export type ProjectionScenario = "conservative" | "base" | "optimistic";
export type AssumptionType = "annual_per_share" | "monthly_per_share" | "weekly_per_share" | "none";

export interface Asset {
  id: string;
  ticker: string;
  name: string;
  market: Market;
  asset_type: AssetType;
  dividend_frequency: DividendFrequency;
  default_color: string;
  display_order: number;
  is_active: boolean;
  created_at: string;
}

export interface Holding {
  id: string;
  asset_id: string;
  shares: string;
  average_cost_krw: string | null;
  updated_at: string;
  created_at: string;
}

export interface ActualDividend {
  id: string;
  asset_id: string;
  paid_date: string;
  gross_amount_krw: string;
  memo: string | null;
  created_at: string;
  updated_at: string;
}

export interface InvestmentRule {
  id: string;
  asset_id: string;
  rule_type: RuleType;
  amount_krw: string | null;
  shares: string | null;
  weekday: number | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface Goal {
  id: string;
  label: string;
  target_amount_krw: string;
  created_at: string;
  updated_at: string;
}

export interface AppSettings {
  id: string;
  exchange_rate: string;
  tax_mode: string;
  counter_animation_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface DividendAssumption {
  id: string;
  asset_id: string;
  assumption_type: AssumptionType;
  annual_dividend_per_share: string | null;
  monthly_dividend_per_share: string | null;
  weekly_dividend_per_share: string | null;
  source_note: string | null;
  updated_at: string;
  is_active: boolean;
}

export interface AssetCatalogMeta {
  ticker: string;
  currentPrice: string;
  priceCurrency: "USD" | "KRW";
  metadataUpdatedAt: string;
}

export interface HoldingWithAsset extends Holding {
  asset: Asset;
}

export interface RuleWithAsset extends InvestmentRule {
  asset: Asset;
}

export interface DividendWithAsset extends ActualDividend {
  asset: Asset;
}

export interface DashboardSnapshot {
  assets: Asset[];
  holdings: HoldingWithAsset[];
  actualDividends: DividendWithAsset[];
  rules: RuleWithAsset[];
  goals: Goal[];
  settings: AppSettings;
  assumptions: DividendAssumption[];
}
