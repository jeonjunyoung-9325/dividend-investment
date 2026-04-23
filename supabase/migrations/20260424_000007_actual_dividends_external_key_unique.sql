delete from public.actual_dividends target
using public.actual_dividends duplicate
where target.id < duplicate.id
  and target.external_key is not null
  and target.external_key = duplicate.external_key;

drop index if exists public.actual_dividends_external_key_idx;

create unique index if not exists actual_dividends_external_key_idx
on public.actual_dividends (external_key);
