-- Falcon Render AI — migration 0003: interior design module.
-- Adds the job mode (exterior sketch->render / interior blank-room->design)
-- and the interior room type. Safe to run once; IF NOT EXISTS guards make
-- re-runs harmless. Existing rows default to 'exterior'.

alter table public.jobs
  add column if not exists mode text not null default 'exterior';

alter table public.jobs
  add column if not exists room_type text;
