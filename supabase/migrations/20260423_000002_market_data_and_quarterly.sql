alter table public.assets
  add column if not exists price_provider text,
  add column if not exists quote_symbol text,
  add column if not exists quote_market text;

alter table public.holdings
  add column if not exists last_synced_at timestamptz;

alter table public.app_settings
  add column if not exists auto_exchange_rate_enabled boolean not null default true,
  add column if not exists auto_broker_sync_enabled boolean not null default true;

alter table public.dividend_assumptions
  add column if not exists quarterly_dividend_per_share numeric(24, 8),
  add column if not exists distribution_months smallint[];

alter table public.dividend_assumptions
  drop constraint if exists dividend_assumptions_assumption_type_check;

alter table public.dividend_assumptions
  add constraint dividend_assumptions_assumption_type_check
  check (
    assumption_type in (
      'annual_per_share',
      'quarterly_per_share',
      'monthly_per_share',
      'weekly_per_share',
      'none'
    )
  );

create table if not exists public.market_quotes (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.assets(id) on delete cascade,
  price numeric(24, 8) not null,
  currency text not null,
  provider text not null,
  fetched_at timestamptz not null,
  is_stale boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (asset_id)
);

create table if not exists public.fx_rates (
  id uuid primary key default gen_random_uuid(),
  pair text not null unique,
  rate numeric(16, 6) not null,
  provider text not null,
  fetched_at timestamptz not null,
  is_stale boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.market_quotes disable row level security;
alter table public.fx_rates disable row level security;

drop trigger if exists set_market_quotes_updated_at on public.market_quotes;
create trigger set_market_quotes_updated_at
before update on public.market_quotes
for each row execute function public.set_updated_at();

drop trigger if exists set_fx_rates_updated_at on public.fx_rates;
create trigger set_fx_rates_updated_at
before update on public.fx_rates
for each row execute function public.set_updated_at();
