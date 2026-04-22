alter table public.holdings
  add column if not exists synced_shares numeric(24, 8),
  add column if not exists synced_average_cost_krw numeric(24, 2),
  add column if not exists synced_value_krw numeric(24, 2);

alter table public.app_settings
  add column if not exists portfolio_data_source text not null default 'api_preferred';

alter table public.app_settings
  drop constraint if exists app_settings_portfolio_data_source_check;

alter table public.app_settings
  add constraint app_settings_portfolio_data_source_check
  check (portfolio_data_source in ('manual', 'api_preferred'));
