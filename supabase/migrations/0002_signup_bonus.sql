-- Falcon Render AI — migration 0002: signup credit bonus
-- Run in Supabase Dashboard → SQL Editor (service_role context).
-- ADR 0004 (freemium model): every new user gets 30 free credits on signup.
--
-- This REPLACES the handle_new_user() from 0001_initial.sql. The existing
-- trigger on_auth_user_created already calls public.handle_new_user(), so
-- replacing the function is enough — no trigger changes needed.
--
-- Idempotent: if a profile row already exists for the user (e.g. created
-- before this migration), no bonus is granted — early users keep their
-- existing balance instead of being double-credited.

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email, credits)
  values (new.id, new.email, 30)
  on conflict (id) do nothing;
  if found then
    -- Row was actually inserted (not a conflict skip): grant the bonus.
    insert into public.credit_ledger (user_id, delta, reason)
    values (new.id, 30, 'grant');
  end if;
  return new;
end;
$$;

-- The trigger from 0001 already exists and calls this function; verify:
-- select * from pg_trigger where tgname = 'on_auth_user_created';
