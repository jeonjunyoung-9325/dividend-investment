alter table public.actual_dividends
  drop constraint if exists actual_dividends_source_check;

alter table public.actual_dividends
  add constraint actual_dividends_source_check
  check (source in ('manual', 'kis_domestic_period_rights', 'kis_overseas_rights_balance'));
