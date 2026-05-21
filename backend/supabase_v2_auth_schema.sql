-- AI SecureWatch V2 Supabase Auth schema.
--
-- Manual setup:
-- 1. Open Supabase Dashboard.
-- 2. Go to SQL Editor.
-- 3. Paste this full file.
-- 4. Run it once.
--
-- This file creates only the V2 profiles foundation. It does not add GitHub
-- App tables, repository tables, Discord webhook tables, or detection
-- migrations.

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  display_name text,
  avatar_url text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_profiles_updated_at on public.profiles;

create trigger set_profiles_updated_at
before update on public.profiles
for each row
execute function public.set_updated_at();

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  metadata jsonb;
  fallback_name text;
begin
  metadata = coalesce(new.raw_user_meta_data, '{}'::jsonb);
  fallback_name = nullif(split_part(coalesce(new.email, ''), '@', 1), '');

  insert into public.profiles (
    id,
    email,
    display_name,
    avatar_url
  )
  values (
    new.id,
    new.email,
    coalesce(
      nullif(metadata ->> 'name', ''),
      nullif(metadata ->> 'user_name', ''),
      fallback_name
    ),
    nullif(metadata ->> 'avatar_url', '')
  )
  on conflict (id) do update
  set
    email = excluded.email,
    display_name = coalesce(public.profiles.display_name, excluded.display_name),
    avatar_url = coalesce(public.profiles.avatar_url, excluded.avatar_url);

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
after insert on auth.users
for each row
execute function public.handle_new_user();

alter table public.profiles enable row level security;

drop policy if exists "profiles_select_own" on public.profiles;

create policy "profiles_select_own"
on public.profiles
for select
to authenticated
using (auth.uid() = id);

drop policy if exists "profiles_update_own" on public.profiles;

create policy "profiles_update_own"
on public.profiles
for update
to authenticated
using (auth.uid() = id)
with check (auth.uid() = id);

grant select, update on public.profiles to authenticated;

-- Backfill profiles for auth users that already existed before this trigger
-- was installed. Safe to run multiple times.
insert into public.profiles (
  id,
  email,
  display_name,
  avatar_url
)
select
  users.id,
  users.email,
  coalesce(
    nullif(users.raw_user_meta_data ->> 'name', ''),
    nullif(users.raw_user_meta_data ->> 'user_name', ''),
    nullif(split_part(coalesce(users.email, ''), '@', 1), '')
  ) as display_name,
  nullif(users.raw_user_meta_data ->> 'avatar_url', '') as avatar_url
from auth.users as users
on conflict (id) do update
set
  email = excluded.email,
  display_name = coalesce(public.profiles.display_name, excluded.display_name),
  avatar_url = coalesce(public.profiles.avatar_url, excluded.avatar_url);
