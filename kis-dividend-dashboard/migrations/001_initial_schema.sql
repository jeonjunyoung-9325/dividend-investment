create schema if not exists kis_dashboard;
revoke all on schema kis_dashboard from public, anon, authenticated;

create or replace function kis_dashboard.set_updated_at() returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists kis_dashboard.sync_runs (
  id varchar(36) primary key,
  started_at timestamptz not null,
  finished_at timestamptz,
  status varchar(24) not null check (status in ('running', 'success', 'partial', 'failed')),
  domestic_status varchar(24) not null default 'pending',
  overseas_status varchar(24) not null default 'pending',
  dividend_status varchar(24) not null default 'pending',
  exchange_rate_status varchar(24) not null default 'pending',
  message text,
  records_inserted integer not null default 0 check (records_inserted >= 0),
  records_updated integer not null default 0 check (records_updated >= 0),
  created_at timestamptz not null default now()
);
create index if not exists ix_sync_runs_started_at on kis_dashboard.sync_runs (started_at desc);

create table if not exists kis_dashboard.portfolio_snapshots (
  id varchar(36) primary key,
  sync_run_id varchar(36) not null references kis_dashboard.sync_runs(id) on delete cascade,
  snapshot_at timestamptz not null,
  market varchar(16) not null check (market in ('domestic', 'overseas')),
  exchange varchar(16) not null default '', symbol varchar(32) not null, name varchar(200) not null,
  quantity numeric(28,8) not null check (quantity >= 0),
  available_quantity numeric(28,8), average_price numeric(28,8), current_price numeric(28,8),
  purchase_amount numeric(28,8), evaluation_amount numeric(28,8), profit_loss numeric(28,8),
  profit_rate numeric(18,8), currency varchar(3) not null,
  krw_exchange_rate numeric(24,10) check (krw_exchange_rate is null or krw_exchange_rate > 0),
  purchase_amount_krw numeric(28,8), evaluation_amount_krw numeric(28,8),
  profit_loss_krw numeric(28,8), source varchar(64) not null,
  created_at timestamptz not null default now(),
  constraint uq_snapshot_run_asset unique (sync_run_id, market, exchange, symbol)
);
create index if not exists ix_snapshots_time on kis_dashboard.portfolio_snapshots (snapshot_at desc);
create index if not exists ix_snapshots_asset_time on kis_dashboard.portfolio_snapshots (market, exchange, symbol, snapshot_at desc);

create table if not exists kis_dashboard.dividend_import_batches (
  id varchar(36) primary key, file_sha256 varchar(64) not null unique,
  status varchar(24) not null check (status in ('previewed', 'importing', 'completed', 'failed')),
  total_rows integer not null default 0 check (total_rows >= 0),
  inserted_rows integer not null default 0 check (inserted_rows >= 0),
  skipped_rows integer not null default 0 check (skipped_rows >= 0),
  error_rows integer not null default 0 check (error_rows >= 0),
  created_at timestamptz not null default now(), finished_at timestamptz
);

create table if not exists kis_dashboard.dividend_payments (
  id varchar(36) primary key,
  market varchar(16) not null check (market in ('domestic', 'overseas')),
  exchange varchar(16) not null default '', symbol varchar(32) not null, name varchar(200) not null,
  ex_dividend_date date, record_date date, payment_date date not null,
  quantity_at_record_date numeric(28,8), gross_amount numeric(28,8) not null check (gross_amount >= 0),
  tax_amount numeric(28,8) not null check (tax_amount >= 0),
  net_amount numeric(28,8) not null check (net_amount >= 0), amount_per_share numeric(28,8),
  currency varchar(3) not null, krw_exchange_rate numeric(24,10),
  gross_amount_krw numeric(28,8), tax_amount_krw numeric(28,8), net_amount_krw numeric(28,8),
  source varchar(64) not null, external_id varchar(160), import_hash varchar(64), memo text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create unique index if not exists uq_dividend_payment_external on kis_dashboard.dividend_payments (source, external_id) where external_id is not null;
create unique index if not exists uq_dividend_payment_import_hash on kis_dashboard.dividend_payments (import_hash) where import_hash is not null;
create index if not exists ix_dividend_payments_payment_date on kis_dashboard.dividend_payments (payment_date desc);

create table if not exists kis_dashboard.dividend_events (
  id varchar(36) primary key, event_key varchar(64) not null unique,
  market varchar(16) not null check (market in ('domestic', 'overseas')),
  exchange varchar(16) not null default '', symbol varchar(32) not null,
  ex_dividend_date date, record_date date, payment_date date,
  amount_per_share numeric(28,8) not null check (amount_per_share >= 0),
  currency varchar(3) not null,
  status varchar(24) not null check (status in ('announced', 'announced_unverified', 'confirmed', 'estimated', 'paid', 'cancelled')),
  source varchar(64) not null, fetched_at timestamptz not null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index if not exists ix_dividend_events_asset_date on kis_dashboard.dividend_events (market, exchange, symbol, payment_date desc);

create table if not exists kis_dashboard.exchange_rates (
  id varchar(36) primary key, rate_date date not null,
  base_currency varchar(3) not null, quote_currency varchar(3) not null,
  rate numeric(24,10) not null check (rate > 0), source varchar(64) not null,
  fetched_at timestamptz not null, created_at timestamptz not null default now(),
  check (base_currency <> quote_currency),
  constraint uq_exchange_rate_observation unique (rate_date, base_currency, quote_currency, source)
);
create index if not exists ix_exchange_rates_lookup on kis_dashboard.exchange_rates (base_currency, quote_currency, rate_date desc, fetched_at desc);

create table if not exists kis_dashboard.kis_token_cache (
  id varchar(36) primary key,
  environment varchar(8) not null check (environment in ('real', 'demo')),
  app_key_fingerprint varchar(64) not null check (app_key_fingerprint ~ '^[0-9a-f]{64}$'),
  encrypted_access_token bytea, token_type varchar(24), issued_at timestamptz,
  expires_at timestamptz, last_requested_at timestamptz,
  state varchar(24) not null default 'empty' check (state in ('empty','requesting','usable','decrypt_failed','request_failed','revoked')),
  request_lease_until timestamptz, blocked_until timestamptz,
  last_failure_kind varchar(40), last_failure_at timestamptz,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  constraint uq_kis_token_identity unique (environment, app_key_fingerprint),
  check (expires_at is null or issued_at is null or expires_at > issued_at),
  check (state <> 'usable' or (encrypted_access_token is not null and token_type is not null and issued_at is not null and expires_at is not null))
);
create index if not exists ix_kis_token_cache_state_expiry on kis_dashboard.kis_token_cache (state, expires_at);

create table if not exists kis_dashboard.app_settings (
  key varchar(160) primary key, value jsonb not null, updated_at timestamptz not null default now()
);

drop trigger if exists set_dividend_payments_updated_at on kis_dashboard.dividend_payments;
create trigger set_dividend_payments_updated_at before update on kis_dashboard.dividend_payments for each row execute function kis_dashboard.set_updated_at();
drop trigger if exists set_dividend_events_updated_at on kis_dashboard.dividend_events;
create trigger set_dividend_events_updated_at before update on kis_dashboard.dividend_events for each row execute function kis_dashboard.set_updated_at();
drop trigger if exists set_kis_token_cache_updated_at on kis_dashboard.kis_token_cache;
create trigger set_kis_token_cache_updated_at before update on kis_dashboard.kis_token_cache for each row execute function kis_dashboard.set_updated_at();
drop trigger if exists set_app_settings_updated_at on kis_dashboard.app_settings;
create trigger set_app_settings_updated_at before update on kis_dashboard.app_settings for each row execute function kis_dashboard.set_updated_at();

revoke all on kis_dashboard.kis_token_cache from anon, authenticated;
revoke all on kis_dashboard.sync_runs, kis_dashboard.portfolio_snapshots, kis_dashboard.dividend_payments from anon, authenticated;
revoke all on kis_dashboard.dividend_events, kis_dashboard.exchange_rates, kis_dashboard.app_settings from anon, authenticated;
revoke all on kis_dashboard.dividend_import_batches from anon, authenticated;
revoke all on all sequences in schema kis_dashboard from public, anon, authenticated;
revoke all on all functions in schema kis_dashboard from public, anon, authenticated;
alter default privileges for role postgres in schema kis_dashboard revoke all on tables from public, anon, authenticated;
alter default privileges for role postgres in schema kis_dashboard revoke all on sequences from public, anon, authenticated;
alter default privileges for role postgres in schema kis_dashboard revoke all on functions from public, anon, authenticated;
