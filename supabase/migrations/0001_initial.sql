-- Falcon Render AI — initial Supabase schema
-- Run in Supabase Dashboard → SQL Editor (service_role context)
-- ADR 0002 (supabase) + ADR 0003 (credit model)

-- ============ profiles ============
create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  credits integer not null default 0 check (credits >= 0),
  free_render_used boolean not null default false,
  created_at timestamptz not null default now()
);

-- ============ jobs ============
create table public.jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles (id) on delete set null,
  status text not null default 'queued'
    check (status in ('queued','processing','succeeded','failed')),
  lighting text not null,
  style text not null,
  sketch_path text not null,
  edge_path text not null,
  reference_path text,
  render_path text,
  fidelity_score numeric check (fidelity_score is null or (fidelity_score >= 0 and fidelity_score <= 1)),
  fidelity_attempts integer not null default 0,
  credits_charged integer not null default 0,
  error text,
  created_at timestamptz not null default now()
);
create index jobs_user_idx on public.jobs (user_id, created_at desc);

-- ============ credit_ledger ============
create table public.credit_ledger (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  delta integer not null check (delta <> 0),
  reason text not null check (reason in ('purchase','render','free_trial','refund','grant')),
  job_id uuid references public.jobs (id) on delete set null,
  created_at timestamptz not null default now()
);
create index ledger_user_idx on public.credit_ledger (user_id, created_at desc);

-- ============ anonymous free-trial tracking ============
-- one free render per device/IP hash, no signup (ADR 0002 freemium)
create table public.anonymous_trials (
  id_hash text primary key,
  used_at timestamptz not null default now()
);

-- ============ auto-create profile on signup ============
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ============ RLS ============
alter table public.profiles enable row level security;
alter table public.jobs enable row level security;
alter table public.credit_ledger enable row level security;
alter table public.anonymous_trials enable row level security;

-- profiles: users read/update only their own row (service_role bypasses RLS)
create policy "read own profile"
  on public.profiles for select
  using (auth.uid() = id);
create policy "update own profile"
  on public.profiles for update
  using (auth.uid() = id);

-- jobs: users read only their own jobs; inserts go through backend (service_role)
create policy "read own jobs"
  on public.jobs for select
  using (auth.uid() = user_id);

-- ledger: users read only their own entries
create policy "read own ledger"
  on public.credit_ledger for select
  using (auth.uid() = user_id);

-- anonymous_trials: no direct user access at all (backend only)

-- ============ storage buckets (create in Dashboard → Storage if not via SQL) ============
insert into storage.buckets (id, name, public)
values
  ('sketches', 'sketches', false),
  ('edges', 'edges', false),
  ('references', 'references', false),
  ('renders', 'renders', false)
on conflict (id) do nothing;

-- storage: authenticated users may read only their own renders via signed URLs
-- (backend mints signed URLs with service_role; keep bucket policies deny-by-default)
