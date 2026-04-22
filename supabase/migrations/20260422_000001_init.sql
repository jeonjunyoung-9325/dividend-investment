create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.assets (
  id uuid primary key default gen_random_uuid(),
  ticker text not null unique,
  name text not null,
  market text not null check (market in ('US', 'KR')),
  asset_type text not null check (asset_type in ('core', 'income', 'satellite', 'hedge')),
  dividend_frequency text not null check (dividend_frequency in ('weekly', 'monthly', 'quarterly', 'none')),
  default_color text not null,
  display_order integer not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.holdings (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.assets(id) on delete cascade,
  shares numeric(24, 8) not null default 0,
  average_cost_krw numeric(24, 2),
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (asset_id)
);

create table if not exists public.actual_dividends (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.assets(id) on delete cascade,
  paid_date date not null,
  gross_amount_krw numeric(24, 2) not null,
  memo text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.dividend_assumptions (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.assets(id) on delete cascade,
  assumption_type text not null check (assumption_type in ('annual_per_share', 'monthly_per_share', 'weekly_per_share', 'none')),
  annual_dividend_per_share numeric(24, 8),
  monthly_dividend_per_share numeric(24, 8),
  weekly_dividend_per_share numeric(24, 8),
  source_note text,
  updated_at timestamptz not null default now(),
  is_active boolean not null default true,
  unique (asset_id)
);

create table if not exists public.investment_rules (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.assets(id) on delete cascade,
  rule_type text not null check (rule_type in ('daily', 'weekly', 'monthly')),
  amount_krw numeric(24, 2),
  shares numeric(24, 8),
  weekday integer check (weekday between 0 and 6),
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.goals (
  id uuid primary key default gen_random_uuid(),
  label text not null,
  target_amount_krw numeric(24, 2) not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.app_settings (
  id uuid primary key default gen_random_uuid(),
  exchange_rate numeric(16, 4) not null default 1365.5000,
  tax_mode text not null default 'gross',
  counter_animation_enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.assets disable row level security;
alter table public.holdings disable row level security;
alter table public.actual_dividends disable row level security;
alter table public.dividend_assumptions disable row level security;
alter table public.investment_rules disable row level security;
alter table public.goals disable row level security;
alter table public.app_settings disable row level security;

drop trigger if exists set_holdings_updated_at on public.holdings;
create trigger set_holdings_updated_at
before update on public.holdings
for each row execute function public.set_updated_at();

drop trigger if exists set_actual_dividends_updated_at on public.actual_dividends;
create trigger set_actual_dividends_updated_at
before update on public.actual_dividends
for each row execute function public.set_updated_at();

drop trigger if exists set_dividend_assumptions_updated_at on public.dividend_assumptions;
create trigger set_dividend_assumptions_updated_at
before update on public.dividend_assumptions
for each row execute function public.set_updated_at();

drop trigger if exists set_investment_rules_updated_at on public.investment_rules;
create trigger set_investment_rules_updated_at
before update on public.investment_rules
for each row execute function public.set_updated_at();

drop trigger if exists set_goals_updated_at on public.goals;
create trigger set_goals_updated_at
before update on public.goals
for each row execute function public.set_updated_at();

drop trigger if exists set_app_settings_updated_at on public.app_settings;
create trigger set_app_settings_updated_at
before update on public.app_settings
for each row execute function public.set_updated_at();
