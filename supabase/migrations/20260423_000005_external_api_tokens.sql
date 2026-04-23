create table if not exists public.external_api_tokens (
  provider text primary key,
  access_token text not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.external_api_tokens disable row level security;

drop trigger if exists set_external_api_tokens_updated_at on public.external_api_tokens;
create trigger set_external_api_tokens_updated_at
before update on public.external_api_tokens
for each row execute function public.set_updated_at();
