insert into public.assets (
  id,
  ticker,
  name,
  market,
  asset_type,
  dividend_frequency,
  default_color,
  display_order,
  price_provider,
  quote_symbol,
  quote_market,
  is_active
)
values (
  '10000000-0000-0000-0000-000000000012',
  'JEPQ',
  'JPMorgan Nasdaq Equity Premium Income ETF',
  'US',
  'income',
  'monthly',
  '#2F7A57',
  12,
  'kis',
  'JEPQ',
  'NAS',
  true
)
on conflict (id) do update
set
  ticker = excluded.ticker,
  name = excluded.name,
  market = excluded.market,
  asset_type = excluded.asset_type,
  dividend_frequency = excluded.dividend_frequency,
  default_color = excluded.default_color,
  display_order = excluded.display_order,
  price_provider = excluded.price_provider,
  quote_symbol = excluded.quote_symbol,
  quote_market = excluded.quote_market,
  is_active = excluded.is_active;

insert into public.holdings (asset_id, shares, average_cost_krw)
values ('10000000-0000-0000-0000-000000000012', 0, null)
on conflict (asset_id) do nothing;

insert into public.dividend_assumptions (
  asset_id,
  assumption_type,
  annual_dividend_per_share,
  quarterly_dividend_per_share,
  monthly_dividend_per_share,
  weekly_dividend_per_share,
  distribution_months,
  source_note,
  is_active
)
values (
  '10000000-0000-0000-0000-000000000012',
  'monthly_per_share',
  null,
  null,
  0.56100500,
  null,
  null,
  'JPMorgan 2026-05-31 공식 NAV 61.48 USD × 12개월 배당수익률 10.95% ÷ 12 단순 추정',
  true
)
on conflict (asset_id) do nothing;
