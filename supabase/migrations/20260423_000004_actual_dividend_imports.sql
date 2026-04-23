alter table public.actual_dividends
  add column if not exists source text not null default 'manual',
  add column if not exists external_key text,
  add column if not exists tax_amount_krw numeric(24, 2),
  add column if not exists imported_at timestamptz;

alter table public.actual_dividends
  drop constraint if exists actual_dividends_source_check;

alter table public.actual_dividends
  add constraint actual_dividends_source_check
  check (source in ('manual', 'kis_domestic_period_rights'));

create unique index if not exists actual_dividends_external_key_idx
on public.actual_dividends (external_key)
where external_key is not null;

delete from public.actual_dividends
where id in (
  '60000000-0000-0000-0000-000000000001',
  '60000000-0000-0000-0000-000000000002',
  '60000000-0000-0000-0000-000000000003',
  '60000000-0000-0000-0000-000000000004'
);
