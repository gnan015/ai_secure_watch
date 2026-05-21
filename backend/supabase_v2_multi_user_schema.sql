-- AI SecureWatch V2 Supabase Multi-User Schema
--
-- Manual setup:
-- 1. Open Supabase Dashboard.
-- 2. Go to SQL Editor.
-- 3. Paste this full file.
-- 4. Run it once.
--
-- This file creates tables, triggers, indexes, and RLS policies for multi-user isolation.
-- It isolates the new multi-user tables and detections_v2 table from the V1 detections table.

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
  created_at timestamptz not null default now()
);

-- workspace_members table
create table if not exists public.workspace_members (
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  role text not null default 'member', -- e.g., 'owner', 'admin', 'member'
  created_at timestamptz not null default now(),
  primary key (workspace_id, user_id)
);

-- github_installations table
create table if not exists public.github_installations (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  installation_id bigint not null unique,
  account_login text not null,
  account_type text not null default 'User', -- e.g., 'User', 'Organization'
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
  default_branch text not null default 'main',
  monitoring_enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- discord_webhooks table
create table if not exists public.discord_webhooks (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  webhook_url text not null,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- scan_events table
create table if not exists public.scan_events (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  repository_id uuid not null references public.repositories(id) on delete cascade,
  github_delivery_id text,
  commit_sha text not null,
  status text not null default 'queued', -- e.g., 'queued', 'scanning', 'completed', 'failed'
  created_at timestamptz not null default now()
);

-- detections_v2 table (isolated from V1 detections)
create table if not exists public.detections_v2 (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  repository_id uuid references public.repositories(id) on delete cascade,
  scan_event_id uuid references public.scan_events(id) on delete set null,

  repo_full_name text not null,
  repo_owner text,
  repo_name text,
  branch text,
  commit_sha text,

  file_path text not null,
  line_number integer,

  secret_type text not null,
  masked_value text not null,
  detection_method text,
  entropy_score numeric,

  severity text not null,
  confidence_score numeric,
  ai_reasoning text,
  ai_recommendation text,

  status text not null default 'open', -- e.g., 'open', 'resolved', 'dismissed'

  pusher_name text,
  pusher_email text,

  detected_at timestamptz not null default now(),
  resolved_at timestamptz
);

-- ==========================================
-- 2. Indexes for Performance
-- ==========================================

create index if not exists idx_workspaces_owner_user_id on public.workspaces(owner_user_id);
create index if not exists idx_workspace_members_user_id on public.workspace_members(user_id);
create index if not exists idx_github_installations_workspace_id on public.github_installations(workspace_id);
create index if not exists idx_repositories_workspace_id on public.repositories(workspace_id);
create index if not exists idx_repositories_github_installation_id on public.repositories(github_installation_id);
create index if not exists idx_discord_webhooks_workspace_id on public.discord_webhooks(workspace_id);
create index if not exists idx_scan_events_workspace_id on public.scan_events(workspace_id);
create index if not exists idx_scan_events_repository_id on public.scan_events(repository_id);

create index if not exists idx_detections_v2_workspace_id on public.detections_v2(workspace_id);
create index if not exists idx_detections_v2_repository_id on public.detections_v2(repository_id);
create index if not exists idx_detections_v2_severity on public.detections_v2(severity);
create index if not exists idx_detections_v2_status on public.detections_v2(status);
create index if not exists idx_detections_v2_detected_at on public.detections_v2(detected_at);

-- ==========================================
-- 3. Automatic updated_at Triggers
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

-- discord_webhooks updated_at trigger
drop trigger if exists set_discord_webhooks_updated_at on public.discord_webhooks;
create trigger set_discord_webhooks_updated_at
before update on public.discord_webhooks
for each row
execute function public.set_updated_at();

-- ==========================================
-- 4. Default Workspace Auto-Provisioning
-- ==========================================

-- Function to handle workspace creation on profile creation
create or replace function public.handle_new_profile()
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
  workspace_name := coalesce(new.display_name, 'Personal') || ' Workspace';

  -- Create a default workspace for the new profile
  insert into public.workspaces (id, owner_user_id, name)
  values (new_workspace_id, new.id, workspace_name);

  -- Add the profile owner to the workspace_members
  insert into public.workspace_members (workspace_id, user_id, role)
  values (new_workspace_id, new.id, 'owner');

  return new;
end;
$$;

-- Trigger to run handle_new_profile
drop trigger if exists on_profile_created on public.profiles;
create trigger on_profile_created
after insert on public.profiles
for each row
execute function public.handle_new_profile();

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
    ws_name := coalesce(profile_rec.display_name, 'Personal') || ' Workspace';
    
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

-- Enable RLS on all tables
alter table public.workspaces enable row level security;
alter table public.workspace_members enable row level security;
alter table public.github_installations enable row level security;
alter table public.repositories enable row level security;
alter table public.discord_webhooks enable row level security;
alter table public.scan_events enable row level security;
alter table public.detections_v2 enable row level security;

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

-- 5c. github_installations Policies
drop policy if exists "github_installations_select" on public.github_installations;
create policy "github_installations_select" on public.github_installations
for select to authenticated
using (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
  or workspace_id in (select public.get_workspaces_for_user(auth.uid()))
);

drop policy if exists "github_installations_insert" on public.github_installations;
create policy "github_installations_insert" on public.github_installations
for insert to authenticated
with check (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
);

drop policy if exists "github_installations_update" on public.github_installations;
create policy "github_installations_update" on public.github_installations
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

drop policy if exists "github_installations_delete" on public.github_installations;
create policy "github_installations_delete" on public.github_installations
for delete to authenticated
using (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
);

-- 5d. repositories Policies
drop policy if exists "repositories_select" on public.repositories;
create policy "repositories_select" on public.repositories
for select to authenticated
using (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
  or workspace_id in (select public.get_workspaces_for_user(auth.uid()))
);

drop policy if exists "repositories_insert" on public.repositories;
create policy "repositories_insert" on public.repositories
for insert to authenticated
with check (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
);

drop policy if exists "repositories_update" on public.repositories;
create policy "repositories_update" on public.repositories
for update to authenticated
using (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
  or workspace_id in (select public.get_workspaces_for_user(auth.uid()))
)
with check (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
  or workspace_id in (select public.get_workspaces_for_user(auth.uid()))
);

drop policy if exists "repositories_delete" on public.repositories;
create policy "repositories_delete" on public.repositories
for delete to authenticated
using (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
);

-- 5e. discord_webhooks Policies
drop policy if exists "discord_webhooks_select" on public.discord_webhooks;
create policy "discord_webhooks_select" on public.discord_webhooks
for select to authenticated
using (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
  or workspace_id in (select public.get_workspaces_for_user(auth.uid()))
);

drop policy if exists "discord_webhooks_insert" on public.discord_webhooks;
create policy "discord_webhooks_insert" on public.discord_webhooks
for insert to authenticated
with check (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
);

drop policy if exists "discord_webhooks_update" on public.discord_webhooks;
create policy "discord_webhooks_update" on public.discord_webhooks
for update to authenticated
using (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
  or workspace_id in (select public.get_workspaces_for_user(auth.uid()))
)
with check (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
  or workspace_id in (select public.get_workspaces_for_user(auth.uid()))
);

drop policy if exists "discord_webhooks_delete" on public.discord_webhooks;
create policy "discord_webhooks_delete" on public.discord_webhooks
for delete to authenticated
using (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
);

-- 5f. scan_events Policies
drop policy if exists "scan_events_select" on public.scan_events;
create policy "scan_events_select" on public.scan_events
for select to authenticated
using (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
  or workspace_id in (select public.get_workspaces_for_user(auth.uid()))
);

-- Note: scan_events inserts/updates are only handled by the backend service role
-- which bypasses RLS automatically.

-- 5g. detections_v2 Policies
drop policy if exists "detections_v2_select" on public.detections_v2;
create policy "detections_v2_select" on public.detections_v2
for select to authenticated
using (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
  or workspace_id in (select public.get_workspaces_for_user(auth.uid()))
);

drop policy if exists "detections_v2_update" on public.detections_v2;
create policy "detections_v2_update" on public.detections_v2
for update to authenticated
using (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
  or workspace_id in (select public.get_workspaces_for_user(auth.uid()))
)
with check (
  workspace_id in (
    select id from public.workspaces where owner_user_id = auth.uid()
  )
  or workspace_id in (select public.get_workspaces_for_user(auth.uid()))
);

-- Note: detections_v2 inserts are only handled by the backend service role
-- which bypasses RLS automatically.

-- ==========================================
-- 6. Role Permissions Granting
-- ==========================================

grant select, insert, update, delete on public.workspaces to authenticated;
grant select, insert, update, delete on public.workspace_members to authenticated;
grant select, insert, update, delete on public.github_installations to authenticated;
grant select, insert, update, delete on public.repositories to authenticated;
grant select, insert, update, delete on public.discord_webhooks to authenticated;
grant select on public.scan_events to authenticated;
grant select, update on public.detections_v2 to authenticated;
