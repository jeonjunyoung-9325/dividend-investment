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
values
  ('10000000-0000-0000-0000-000000000001', 'QQQ', 'Invesco QQQ Trust', 'US', 'core', 'quarterly', '#3F7BB8', 1, 'kis', 'QQQ', 'NAS', true),
  ('10000000-0000-0000-0000-000000000002', 'VOO', 'Vanguard S&P 500 ETF', 'US', 'core', 'quarterly', '#2F7A57', 2, 'kis', 'VOO', 'AMS', true),
  ('10000000-0000-0000-0000-000000000003', 'JEPI', 'JPMorgan Equity Premium Income ETF', 'US', 'income', 'monthly', '#D28145', 3, 'kis', 'JEPI', 'AMS', true),
  ('10000000-0000-0000-0000-000000000004', 'SCHD', 'Schwab U.S. Dividend Equity ETF', 'US', 'income', 'quarterly', '#538C76', 4, 'kis', 'SCHD', 'AMS', true),
  ('10000000-0000-0000-0000-000000000005', 'O', 'Realty Income', 'US', 'income', 'monthly', '#7A5AF8', 5, 'kis', 'O', 'NYS', true),
  ('10000000-0000-0000-0000-000000000006', 'SOXX', 'iShares Semiconductor ETF', 'US', 'satellite', 'quarterly', '#F97316', 6, 'kis', 'SOXX', 'NAS', true),
  ('10000000-0000-0000-0000-000000000007', 'NVDY', 'YieldMax NVDA Option Income Strategy ETF', 'US', 'income', 'weekly', '#EF4444', 7, 'kis', 'NVDY', 'AMS', true),
  ('10000000-0000-0000-0000-000000000008', 'IAU', 'iShares Gold Trust', 'US', 'hedge', 'none', '#C59A3D', 8, 'kis', 'IAU', 'AMS', true),
  ('10000000-0000-0000-0000-000000000009', 'KODEX 200타겟위클리커버드콜', 'KODEX 200타겟위클리커버드콜', 'KR', 'income', 'monthly', '#2563EB', 9, 'kis', '498400', 'J', true),
  ('10000000-0000-0000-0000-000000000010', 'RISE 200위클리커버드콜', 'RISE 200위클리커버드콜', 'KR', 'income', 'monthly', '#0F766E', 10, 'kis', '475720', 'J', true),
  ('10000000-0000-0000-0000-000000000011', 'KODEX 미국성장커버드콜액티브', 'KODEX 미국성장커버드콜액티브', 'KR', 'income', 'monthly', '#EA580C', 11, 'kis', '0144L0', 'J', true)
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
values
  ('10000000-0000-0000-0000-000000000001', 0, null),
  ('10000000-0000-0000-0000-000000000002', 0, null),
  ('10000000-0000-0000-0000-000000000003', 0, null),
  ('10000000-0000-0000-0000-000000000004', 0, null),
  ('10000000-0000-0000-0000-000000000005', 0, null),
  ('10000000-0000-0000-0000-000000000006', 0, null),
  ('10000000-0000-0000-0000-000000000007', 0, null),
  ('10000000-0000-0000-0000-000000000008', 0, null),
  ('10000000-0000-0000-0000-000000000009', 0, null),
  ('10000000-0000-0000-0000-000000000010', 0, null),
  ('10000000-0000-0000-0000-000000000011', 0, null)
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
values
  ('10000000-0000-0000-0000-000000000001', 'quarterly_per_share', null, 0.75250000, null, null, '{3,6,9,12}', 'QQQ 예상 분기 배당/주 (USD)', true),
  ('10000000-0000-0000-0000-000000000002', 'quarterly_per_share', null, 1.70500000, null, null, '{3,6,9,12}', 'VOO 예상 분기 배당/주 (USD)', true),
  ('10000000-0000-0000-0000-000000000003', 'monthly_per_share', null, null, 0.41000000, null, null, 'JEPI 예상 월 배당/주 (USD)', true),
  ('10000000-0000-0000-0000-000000000004', 'quarterly_per_share', null, 0.68500000, null, null, '{3,6,9,12}', 'SCHD 예상 분기 배당/주 (USD)', true),
  ('10000000-0000-0000-0000-000000000005', 'monthly_per_share', null, null, 0.26300000, null, null, 'O 예상 월 배당/주 (USD)', true),
  ('10000000-0000-0000-0000-000000000006', 'quarterly_per_share', null, 0.98000000, null, null, '{3,6,9,12}', 'SOXX 예상 분기 배당/주 (USD)', true),
  ('10000000-0000-0000-0000-000000000007', 'weekly_per_share', null, null, null, 0.19800000, null, 'NVDY 예상 주 배당/주 (USD)', true),
  ('10000000-0000-0000-0000-000000000008', 'none', null, null, null, null, null, 'IAU 배당 없음', true),
  ('10000000-0000-0000-0000-000000000009', 'monthly_per_share', null, null, 60.00000000, null, null, '국내 커버드콜 월 분배금/주 (KRW)', true),
  ('10000000-0000-0000-0000-000000000010', 'monthly_per_share', null, null, 54.00000000, null, null, '국내 커버드콜 월 분배금/주 (KRW)', true),
  ('10000000-0000-0000-0000-000000000011', 'monthly_per_share', null, null, 70.00000000, null, null, '국내 커버드콜 월 분배금/주 (KRW)', true)
on conflict (asset_id) do update
set
  assumption_type = excluded.assumption_type,
  annual_dividend_per_share = excluded.annual_dividend_per_share,
  quarterly_dividend_per_share = excluded.quarterly_dividend_per_share,
  monthly_dividend_per_share = excluded.monthly_dividend_per_share,
  weekly_dividend_per_share = excluded.weekly_dividend_per_share,
  distribution_months = excluded.distribution_months,
  source_note = excluded.source_note,
  is_active = excluded.is_active;

insert into public.app_settings (
  id,
  exchange_rate,
  tax_mode,
  counter_animation_enabled,
  auto_exchange_rate_enabled,
  auto_broker_sync_enabled,
  portfolio_data_source
)
values ('30000000-0000-0000-0000-000000000001', 1365.5000, 'gross', true, true, true, 'api_preferred')
on conflict (id) do update
set
  exchange_rate = excluded.exchange_rate,
  tax_mode = excluded.tax_mode,
  counter_animation_enabled = excluded.counter_animation_enabled,
  auto_exchange_rate_enabled = excluded.auto_exchange_rate_enabled,
  auto_broker_sync_enabled = excluded.auto_broker_sync_enabled,
  portfolio_data_source = excluded.portfolio_data_source;

insert into public.goals (id, label, target_amount_krw)
values ('40000000-0000-0000-0000-000000000001', '월 배당 100만원', 1000000.00)
on conflict (id) do update
set
  label = excluded.label,
  target_amount_krw = excluded.target_amount_krw;

insert into public.investment_rules (id, asset_id, rule_type, amount_krw, shares, weekday, enabled)
values
  ('50000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000002', 'monthly', 200000.00, null, null, true),
  ('50000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', 'monthly', 200000.00, null, null, true),
  ('50000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000004', 'monthly', 100000.00, null, null, true),
  ('50000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000003', 'monthly', 60000.00, null, null, true),
  ('50000000-0000-0000-0000-000000000005', '10000000-0000-0000-0000-000000000006', 'monthly', 60000.00, null, null, true),
  ('50000000-0000-0000-0000-000000000006', '10000000-0000-0000-0000-000000000005', 'monthly', 50000.00, null, null, true),
  ('50000000-0000-0000-0000-000000000007', '10000000-0000-0000-0000-000000000008', 'monthly', 30000.00, null, null, true),
  ('50000000-0000-0000-0000-000000000008', '10000000-0000-0000-0000-000000000007', 'weekly', null, 1.00000000, 1, true),
  ('50000000-0000-0000-0000-000000000009', '10000000-0000-0000-0000-000000000003', 'daily', 1000.00, null, null, true),
  ('50000000-0000-0000-0000-000000000010', '10000000-0000-0000-0000-000000000004', 'daily', 1000.00, null, null, true),
  ('50000000-0000-0000-0000-000000000011', '10000000-0000-0000-0000-000000000005', 'daily', 1000.00, null, null, true)
on conflict (id) do update
set
  asset_id = excluded.asset_id,
  rule_type = excluded.rule_type,
  amount_krw = excluded.amount_krw,
  shares = excluded.shares,
  weekday = excluded.weekday,
  enabled = excluded.enabled;

insert into public.market_quotes (asset_id, price, currency, provider, fetched_at, is_stale)
values
  ('10000000-0000-0000-0000-000000000001', 468.12000000, 'USD', 'seed-fallback', now(), false),
  ('10000000-0000-0000-0000-000000000002', 515.37000000, 'USD', 'seed-fallback', now(), false),
  ('10000000-0000-0000-0000-000000000003', 57.14000000, 'USD', 'seed-fallback', now(), false),
  ('10000000-0000-0000-0000-000000000004', 83.52000000, 'USD', 'seed-fallback', now(), false),
  ('10000000-0000-0000-0000-000000000005', 56.83000000, 'USD', 'seed-fallback', now(), false),
  ('10000000-0000-0000-0000-000000000006', 231.79000000, 'USD', 'seed-fallback', now(), false),
  ('10000000-0000-0000-0000-000000000007', 27.46000000, 'USD', 'seed-fallback', now(), false),
  ('10000000-0000-0000-0000-000000000008', 58.14000000, 'USD', 'seed-fallback', now(), false),
  ('10000000-0000-0000-0000-000000000009', 10525.00000000, 'KRW', 'seed-fallback', now(), false),
  ('10000000-0000-0000-0000-000000000010', 9980.00000000, 'KRW', 'seed-fallback', now(), false),
  ('10000000-0000-0000-0000-000000000011', 12840.00000000, 'KRW', 'seed-fallback', now(), false)
on conflict (asset_id) do update
set
  price = excluded.price,
  currency = excluded.currency,
  provider = excluded.provider,
  fetched_at = excluded.fetched_at,
  is_stale = excluded.is_stale;

insert into public.fx_rates (pair, rate, provider, fetched_at, is_stale)
values ('USD/KRW', 1365.500000, 'seed-fallback', now(), false)
on conflict (pair) do update
set
  rate = excluded.rate,
  provider = excluded.provider,
  fetched_at = excluded.fetched_at,
  is_stale = excluded.is_stale;
