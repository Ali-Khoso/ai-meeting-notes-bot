-- Run once in Supabase SQL Editor. No service-role key is used by this app.
create table if not exists public.meetings (
  owner_id uuid not null references auth.users(id) on delete cascade,
  recording_id text not null check (recording_id ~ '^[1-9][0-9]{0,19}$'),
  title text not null,
  transcript jsonb not null check (jsonb_typeof(transcript) = 'array'),
  summary text not null default '',
  imported_at timestamptz not null default now(),
  primary key (owner_id,recording_id)
);
alter table public.meetings enable row level security;
revoke all on public.meetings from anon;
grant select,insert,update,delete on public.meetings to authenticated;
drop policy if exists "Own meetings only" on public.meetings;
create policy "Own meetings only" on public.meetings for all to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);
