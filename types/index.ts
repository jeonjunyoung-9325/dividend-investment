export type Market = "US" | "KR";
export type AssetType = "core" | "income" | "satellite" | "hedge";
export type DividendFrequency = "weekly" | "monthly" | "quarterly" | "none";
export type RuleType = "daily" | "weekly" | "monthly";
export type ProjectionScenario = "conservative" | "base" | "optimistic";
export type AssumptionType =
  | "annual_per_share"
  | "quarterly_per_share"
  | "monthly_per_share"
  | "weekly_per_share"
  | "none";

export interface Asset {
  id: string;
  ticker: string;
  name: string;
  market: Market;
  asset_type: AssetType;
  dividend_frequency: DividendFrequency;
  default_color: string;
  display_order: number;
  price_provider: string | null;
  quote_symbol: string | null;
  quote_market: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Holding {
  id: string;
  asset_id: string;
  shares: string;
  average_cost_krw: string | null;
  synced_shares: string | null;
  synced_average_cost_krw: string | null;
  synced_value_krw: string | null;
  last_synced_at: string | null;
  updated_at: string;
  created_at: string;
}

export interface ActualDividend {
  id: string;
  asset_id: string;
  paid_date: string;
  gross_amount_krw: string;
  tax_amount_krw: string | null;
  basis_shares: string | null;
  per_share_amount: string | null;
  per_share_currency: string | null;
  base_date: string | null;
  local_record_date: string | null;
  applied_fx_rate: string | null;
  memo: string | null;
  source: "manual" | "kis_domestic_period_rights" | "kis_overseas_rights_balance";
  external_key: string | null;
  imported_at: string | null;
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
  auto_exchange_rate_enabled: boolean;
  auto_broker_sync_enabled: boolean;
  portfolio_data_source: "manual" | "api_preferred";
  created_at: string;
  updated_at: string;
}

export interface DividendAssumption {
  id: string;
  asset_id: string;
  assumption_type: AssumptionType;
  annual_dividend_per_share: string | null;
  quarterly_dividend_per_share: string | null;
  monthly_dividend_per_share: string | null;
  weekly_dividend_per_share: string | null;
  distribution_months: number[] | null;
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

export interface MarketQuote {
  id: string;
  asset_id: string;
  price: string;
  currency: string;
  provider: string;
  fetched_at: string;
  is_stale: boolean;
  created_at: string;
  updated_at: string;
}

export interface FxRate {
  id: string;
  pair: string;
  rate: string;
  provider: string;
  fetched_at: string;
  is_stale: boolean;
  created_at: string;
  updated_at: string;
}

export interface ExternalApiToken {
  provider: string;
  access_token: string;
  expires_at: string;
  created_at: string;
  updated_at: string;
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
  marketQuotes: MarketQuote[];
  fxRates: FxRate[];
}
