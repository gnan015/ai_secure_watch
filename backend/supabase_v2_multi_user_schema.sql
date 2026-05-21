-- AI SecureWatch V2 Supabase Multi-User Schema
--
-- Manual setup:
-- 1. Open Supabase Dashboard.
-- 2. Go to SQL Editor.
-- 3. Paste this full file.
-- 4. Run it once.
--
-- This file contains Phase 3.1 and Phase 3.2 definitions.
-- It does not create Discord webhooks, scan events, or V2 detections.

-- Enable UUID extension if not already enabled
create extension if not exists "uuid-ossp";

-- ==========================================
-- Phase 3.1 Workspaces And Members
-- ==========================================

-- ==========================================
-- 1. Table Definitions (Phase 3.1)
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
-- 2. Indexes for Performance (Phase 3.1)
-- ==========================================

create index if not exists idx_workspaces_owner_user_id on public.workspaces(owner_user_id);
create index if not exists idx_workspace_members_user_id on public.workspace_members(user_id);
create index if not exists idx_workspace_members_workspace_id on public.workspace_members(workspace_id);

-- ==========================================
-- 3. Automatic updated_at Triggers (Phase 3.1)
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
-- 4. Default Workspace Auto-Provisioning (Phase 3.1)
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
-- Helper Functions for RLS (Phase 3.1 & 3.2)
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

-- Helper function to check if a user is an owner or admin of a workspace.
-- Runs with security definer to bypass RLS.
create or replace function public.is_workspace_admin_or_owner(workspace_id uuid, user_id uuid)
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select exists (
    select 1 from public.workspace_members 
    where workspace_members.workspace_id = $1 
      and workspace_members.user_id = $2 
      and workspace_members.role in ('owner', 'admin')
  );
$$;

-- ==========================================
-- 5. Row-Level Security (RLS) Policies (Phase 3.1)
-- ==========================================

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
-- 6. Role Permissions Granting (Phase 3.1)
-- ==========================================

grant select, insert, update, delete on public.workspaces to authenticated;
grant select, insert, update, delete on public.workspace_members to authenticated;


-- ==========================================
-- Phase 3.2 GitHub Installations And Repositories
-- ==========================================

-- ==========================================
-- 1. Table Definitions (Phase 3.2)
-- ==========================================

-- github_installations table
create table if not exists public.github_installations (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  installation_id bigint not null unique,
  account_login text not null,
  account_type text,
  account_id bigint,
  app_slug text,
  installed_by_user_id uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- repositories table
create table if not exists public.repositories (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  github_installation_id uuid not null references public.github_installations(id) on delete cascade,
  github_repo_id bigint not null unique,
  full_name text not null,
  owner text not null,
  name text not null,
  private boolean default false,
  default_branch text,
  html_url text,
  monitoring_enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ==========================================
-- 2. Indexes for Performance (Phase 3.2)
-- ==========================================

create index if not exists idx_github_installations_workspace_id on public.github_installations(workspace_id);
create index if not exists idx_github_installations_installation_id on public.github_installations(installation_id);
create index if not exists idx_github_installations_account_login on public.github_installations(account_login);

create index if not exists idx_repositories_workspace_id on public.repositories(workspace_id);
create index if not exists idx_repositories_github_installation_id on public.repositories(github_installation_id);
create index if not exists idx_repositories_github_repo_id on public.repositories(github_repo_id);
create index if not exists idx_repositories_full_name on public.repositories(full_name);
create index if not exists idx_repositories_monitoring_enabled on public.repositories(monitoring_enabled);

-- ==========================================
-- 3. Automatic updated_at Triggers (Phase 3.2)
-- ==========================================

-- github_installations updated_at trigger
drop trigger if exists set_github_installations_updated_at on public.github_installations;
create trigger set_github_installations_updated_at
before update on public.github_installations
for each row
execute function public.set_updated_at();

-- repositories updated_at trigger
drop trigger if exists set_repositories_updated_at on public.repositories;
create trigger set_repositories_updated_at
before update on public.repositories
for each row
execute function public.set_updated_at();

-- ==========================================
-- 4. Row-Level Security (RLS) Policies (Phase 3.2)
-- ==========================================

alter table public.github_installations enable row level security;
alter table public.repositories enable row level security;

-- github_installations Policies
drop policy if exists "github_installations_select" on public.github_installations;
create policy "github_installations_select" on public.github_installations
for select to authenticated
using (
  workspace_id in (select public.get_workspaces_for_user(auth.uid()))
);

drop policy if exists "github_installations_insert" on public.github_installations;
create policy "github_installations_insert" on public.github_installations
for insert to authenticated
with check (
  public.is_workspace_admin_or_owner(workspace_id, auth.uid())
);

drop policy if exists "github_installations_update" on public.github_installations;
create policy "github_installations_update" on public.github_installations
for update to authenticated
using (
  public.is_workspace_admin_or_owner(workspace_id, auth.uid())
)
with check (
  public.is_workspace_admin_or_owner(workspace_id, auth.uid())
);

drop policy if exists "github_installations_delete" on public.github_installations;
create policy "github_installations_delete" on public.github_installations
for delete to authenticated
using (
  public.is_workspace_admin_or_owner(workspace_id, auth.uid())
);

-- repositories Policies
drop policy if exists "repositories_select" on public.repositories;
create policy "repositories_select" on public.repositories
for select to authenticated
using (
  workspace_id in (select public.get_workspaces_for_user(auth.uid()))
);

drop policy if exists "repositories_insert" on public.repositories;
create policy "repositories_insert" on public.repositories
for insert to authenticated
with check (
  public.is_workspace_admin_or_owner(workspace_id, auth.uid())
);

drop policy if exists "repositories_update" on public.repositories;
create policy "repositories_update" on public.repositories
for update to authenticated
using (
  public.is_workspace_admin_or_owner(workspace_id, auth.uid())
)
with check (
  public.is_workspace_admin_or_owner(workspace_id, auth.uid())
);

drop policy if exists "repositories_delete" on public.repositories;
create policy "repositories_delete" on public.repositories
for delete to authenticated
using (
  public.is_workspace_admin_or_owner(workspace_id, auth.uid())
);

-- ==========================================
-- 5. Role Permissions Granting (Phase 3.2)
-- ==========================================

grant select, insert, update, delete on public.github_installations to authenticated;
grant select, insert, update, delete on public.repositories to authenticated;
