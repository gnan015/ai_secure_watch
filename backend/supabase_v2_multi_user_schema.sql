-- Phase 3.1 Workspaces And Members
--
-- Manual setup:
-- 1. Open Supabase Dashboard.
-- 2. Go to SQL Editor.
-- 3. Paste this full file.
-- 4. Run it once.
--
-- This file creates only the workspaces and workspace_members tables,
-- triggers, indexes, and RLS policies for multi-user isolation.
-- It does not create GitHub installations, repositories, Discord webhooks, or V2 detections.

-- Enable UUID extension if not already enabled
create extension if not exists "uuid-ossp";

-- ==========================================
-- 1. Table Definitions
-- ==========================================

-- workspaces table
create table if not exists public.workspaces (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references public.profiles(id) on delete cascade,
  name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- workspace_members table
create table if not exists public.workspace_members (
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  role text not null default 'owner',
  created_at timestamptz not null default now(),
  primary key (workspace_id, user_id),
  constraint chk_role check (role in ('owner', 'admin', 'member'))
);

-- ==========================================
-- 2. Indexes for Performance
-- ==========================================

create index if not exists idx_workspaces_owner_user_id on public.workspaces(owner_user_id);
create index if not exists idx_workspace_members_user_id on public.workspace_members(user_id);
create index if not exists idx_workspace_members_workspace_id on public.workspace_members(workspace_id);

-- ==========================================
-- 3. Automatic updated_at Triggers
-- ==========================================

-- Ensure set_updated_at helper function exists
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- workspaces updated_at trigger
drop trigger if exists set_workspaces_updated_at on public.workspaces;
create trigger set_workspaces_updated_at
before update on public.workspaces
for each row
execute function public.set_updated_at();

-- ==========================================
-- 4. Default Workspace Auto-Provisioning
-- ==========================================

-- Function to handle workspace creation on profile creation
create or replace function public.handle_new_profile_workspace()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  new_workspace_id uuid;
  workspace_name text;
begin
  new_workspace_id := gen_random_uuid();
  
  if new.display_name is not null and new.display_name <> '' then
    workspace_name := new.display_name || '''s Workspace';
  else
    workspace_name := 'My Workspace';
  end if;

  -- Create default workspace
  insert into public.workspaces (id, owner_user_id, name)
  values (new_workspace_id, new.id, workspace_name)
  on conflict (id) do nothing;

  -- Add the profile owner to the workspace_members as owner
  insert into public.workspace_members (workspace_id, user_id, role)
  values (new_workspace_id, new.id, 'owner')
  on conflict (workspace_id, user_id) do nothing;

  return new;
end;
$$;

-- Trigger to run handle_new_profile_workspace
drop trigger if exists on_profile_created_workspace on public.profiles;
create trigger on_profile_created_workspace
after insert on public.profiles
for each row
execute function public.handle_new_profile_workspace();

-- Backfill workspaces and workspace_members for existing profiles that don't have one
do $$
declare
  profile_rec record;
  new_ws_id uuid;
  ws_name text;
begin
  for profile_rec in 
    select id, display_name from public.profiles
    where id not in (select owner_user_id from public.workspaces)
  loop
    new_ws_id := gen_random_uuid();
    
    if profile_rec.display_name is not null and profile_rec.display_name <> '' then
      ws_name := profile_rec.display_name || '''s Workspace';
    else
      ws_name := 'My Workspace';
    end if;
    
    insert into public.workspaces (id, owner_user_id, name)
    values (new_ws_id, profile_rec.id, ws_name)
    on conflict do nothing;
    
    insert into public.workspace_members (workspace_id, user_id, role)
    values (new_ws_id, profile_rec.id, 'owner')
    on conflict do nothing;
  end loop;
end;
$$;

-- ==========================================
-- 5. Row-Level Security (RLS) Policies
-- ==========================================

-- Helper function to break infinite recursion in workspace membership policies.
-- Runs with security definer to bypass RLS.
create or replace function public.get_workspaces_for_user(user_id uuid)
returns setof uuid
language sql
security definer
set search_path = public
stable
as $$
  select workspace_id from public.workspace_members where user_id = $1;
$$;

-- Enable RLS on both tables
alter table public.workspaces enable row level security;
alter table public.workspace_members enable row level security;

-- 5a. workspaces Policies
drop policy if exists "workspaces_select" on public.workspaces;
create policy "workspaces_select" on public.workspaces
for select to authenticated
using (
  owner_user_id = auth.uid()
  or id in (select public.get_workspaces_for_user(auth.uid()))
);

drop policy if exists "workspaces_insert" on public.workspaces;
create policy "workspaces_insert" on public.workspaces
for insert to authenticated
with check (
  owner_user_id = auth.uid()
);

drop policy if exists "workspaces_update" on public.workspaces;
create policy "workspaces_update" on public.workspaces
for update to authenticated
using (
  owner_user_id = auth.uid()
)
with check (
  owner_user_id = auth.uid()
);

drop policy if exists "workspaces_delete" on public.workspaces;
create policy "workspaces_delete" on public.workspaces
for delete to authenticated
using (
  owner_user_id = auth.uid()
);

-- 5b. workspace_members Policies
drop policy if exists "workspace_members_select" on public.workspace_members;
create policy "workspace_members_select" on public.workspace_members
for select to authenticated
using (
  user_id = auth.uid()
  or workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
  or workspace_id in (select public.get_workspaces_for_user(auth.uid()))
);

drop policy if exists "workspace_members_insert" on public.workspace_members;
create policy "workspace_members_insert" on public.workspace_members
for insert to authenticated
with check (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
);

drop policy if exists "workspace_members_update" on public.workspace_members;
create policy "workspace_members_update" on public.workspace_members
for update to authenticated
using (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
)
with check (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
);

drop policy if exists "workspace_members_delete" on public.workspace_members;
create policy "workspace_members_delete" on public.workspace_members
for delete to authenticated
using (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
);

-- ==========================================
-- 6. Role Permissions Granting
-- ==========================================

grant select, insert, update, delete on public.workspaces to authenticated;
grant select, insert, update, delete on public.workspace_members to authenticated;
