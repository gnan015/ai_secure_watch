# AI SecureWatch V2 Phase 3: Multi-User Database Schema

This document details the database schema design and Row-Level Security (RLS) structure for **AI SecureWatch V2 Phase 3.1, 3.2 & 3.3**. The goal of this phase is to establish the foundation for multi-user ownership.

The schema is defined in [supabase_v2_multi_user_schema.sql](file:///C:/ai%20secure%20watch/backend/supabase_v2_multi_user_schema.sql).

---

## Phase 3.1 Workspaces And Members

### 1. Schema Architecture & Relations

We introduce multi-user tenant boundaries through **Workspaces**. Profiles are linked to workspaces via `workspace_members`, which supports multiple roles per workspace.

#### Table: `public.workspaces`
- `id` uuid primary key default `gen_random_uuid()`
- `owner_user_id` uuid not null references `public.profiles(id)` on delete cascade
- `name` text not null
- `created_at` timestamptz not null default `now()`
- `updated_at` timestamptz not null default `now()`

#### Table: `public.workspace_members`
- `workspace_id` uuid not null references `public.workspaces(id)` on delete cascade
- `user_id` uuid not null references `public.profiles(id)` on delete cascade
- `role` text not null default `'owner'`
- `created_at` timestamptz not null default `now()`
- primary key (`workspace_id`, `user_id`)
- check constraint `chk_role`: restricts `role` to values: `'owner'`, `'admin'`, `'member'`

---

### 2. Workspace Auto-Provisioning & Triggers

To make onboarding seamless, we auto-provision a default personal workspace for every user:
1. **New Users**: A trigger (`on_profile_created_workspace`) listens for inserts to `public.profiles` and fires the function `handle_new_profile_workspace()` to create a workspace named `"<display_name>'s Workspace"` (or `"My Workspace"` if display_name is missing) and insert a `workspace_members` owner record.
2. **Existing Users**: A migration backfill script automatically crawls existing users without a workspace and provisions one for them safely.

---

### 3. Row-Level Security (RLS) & Access Isolation

RLS is enabled on both `public.workspaces` and `public.workspace_members`.

#### Resolving RLS Policy Infinite Recursion
Checking if a user belongs to a workspace can lead to infinite loops if we query `workspace_members` from an RLS policy on the same table. To solve this, we introduce a **Security Definer** helper function:
```sql
create or replace function public.get_workspaces_for_user(user_id uuid)
returns setof uuid
language sql
security definer
set search_path = public
stable
as $$
  select workspace_id from public.workspace_members where user_id = $1;
$$;
```
This function executes with the privileges of the database owner (bypassing RLS on `workspace_members`) to resolve memberships safely.

#### Policy Rules Matrix

| Table | SELECT | INSERT | UPDATE | DELETE |
| :--- | :--- | :--- | :--- | :--- |
| **`workspaces`** | Workspace Members | Authenticated users (where `owner_user_id = auth.uid()`) | Workspace Owners (where `owner_user_id = auth.uid()`) | Workspace Owners (where `owner_user_id = auth.uid()`) |
| **`workspace_members`** | Workspace Members | Workspace Owners | Workspace Owners | Workspace Owners |

---

## Phase 3.2 GitHub Installations And Repositories

### 1. Schema Architecture & Relations

We introduce structures to register GitHub App integrations and select specific repositories for secret scanning:

#### Table: `public.github_installations`
- `id` uuid primary key default `gen_random_uuid()`
- `workspace_id` uuid not null references `public.workspaces(id)` on delete cascade
- `installation_id` bigint not null unique (the identifier provided by GitHub)
- `account_login` text not null
- `account_type` text (e.g., `'User'`, `'Organization'`)
- `account_id` bigint (GitHub account ID)
- `app_slug` text (identifier of the GitHub App)
- `installed_by_user_id` uuid references `public.profiles(id)` on delete set null
- `created_at` timestamptz not null default `now()`
- `updated_at` timestamptz not null default `now()`

#### Table: `public.repositories`
- `id` uuid primary key default `gen_random_uuid()`
- `workspace_id` uuid not null references `public.workspaces(id)` on delete cascade
- `github_installation_id` uuid not null references `public.github_installations(id)` on delete cascade
- `github_repo_id` bigint not null unique (the identifier provided by GitHub)
- `full_name` text not null
- `owner` text not null
- `name` text not null
- `private` boolean default `false`
- `default_branch` text
- `html_url` text
- `monitoring_enabled` boolean not null default `true` (enables or disables active commit scanning)
- `created_at` timestamptz not null default `now()`
- `updated_at` timestamptz not null default `now()`

---

### 2. Row-Level Security (RLS) & Access Isolation

RLS is enabled on both `public.github_installations` and `public.repositories`. 

#### Helper Function for Write Actions
To grant insert/update/delete permissions to owners and admins only, we define a helper function `is_workspace_admin_or_owner(workspace_id uuid, user_id uuid)`:
```sql
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
```
This bypasses RLS on `workspace_members` safely to verify authorization rules.

#### Policy Rules Matrix

| Table | SELECT | INSERT | UPDATE | DELETE |
| :--- | :--- | :--- | :--- | :--- |
| **`github_installations`** | Workspace Members | Workspace Owners/Admins | Workspace Owners/Admins | Workspace Owners/Admins |
| **`repositories`** | Workspace Members | Workspace Owners/Admins | Workspace Owners/Admins (including `monitoring_enabled`) | Workspace Owners/Admins |

---

## Phase 3.3 Discord Webhooks

### 1. Schema Architecture & Relations

We introduce structures to store workspace-level configurations for Discord notifications:

#### Table: `public.discord_webhooks`
- `id` uuid primary key default `gen_random_uuid()`
- `workspace_id` uuid not null references `public.workspaces(id)` on delete cascade
- `name` text not null default `'Default Discord Webhook'`
- `webhook_url_ciphertext` text not null (stores the encrypted URL value for data security)
- `webhook_url_last4` text (stores the last 4 characters of the URL for dashboard mask preview)
- `enabled` boolean not null default `true`
- `last_tested_at` timestamptz
- `last_error` text
- `created_by_user_id` uuid references `public.profiles(id)` on delete set null
- `created_at` timestamptz not null default `now()`
- `updated_at` timestamptz not null default `now()`

> [!IMPORTANT]
> The webhook URL is sensitive and must not be exposed in raw form to the frontend. It is stored as ciphertext (`webhook_url_ciphertext`) and decrypted only on the backend during webhook alerting.

---

### 2. Row-Level Security (RLS) & Access Isolation

RLS is enabled on `public.discord_webhooks`. 

#### Policy Rules Matrix

| Table | SELECT | INSERT | UPDATE | DELETE |
| :--- | :--- | :--- | :--- | :--- |
| **`discord_webhooks`** | Workspace Members | Workspace Owners/Admins | Workspace Owners/Admins | Workspace Owners/Admins |

---

### 3. Non-Implemented Components (Deferred to Phase 3.4+)

To preserve the stability of the V1 features and control scope progression, the following are intentionally deferred:
- **Scan events / V2 detections** tables (`scan_events`, `detections_v2`) are not created yet.
- **V1 Detections table** (`detections`) is **not** modified or migrated.
- **Webhook processing** and **scanner logic** remain unchanged.
- **Discord webhooks settings UI** on the dashboard is not implemented yet.
- **Backend webhook test endpoints** are not created yet.
- **GitHub App oauth callback, tokens, and routing backend APIs** are not yet implemented.
