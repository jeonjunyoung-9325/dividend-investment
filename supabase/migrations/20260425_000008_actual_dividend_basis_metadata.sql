alter table public.actual_dividends
  add column if not exists basis_shares numeric(24, 8),
  add column if not exists per_share_amount numeric(24, 8),
  add column if not exists per_share_currency text,
  add column if not exists base_date date,
  add column if not exists local_record_date date,
  add column if not exists applied_fx_rate numeric(16, 4);
