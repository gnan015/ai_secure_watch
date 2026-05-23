# AI SecureWatch V2 Phase 3: Multi-User Database Schema

This document details the database schema design and Row-Level Security (RLS) structure for **AI SecureWatch V2 Phase 3 (3.1 to 3.6)**. The goal of this phase is to establish the foundation for multi-user ownership.

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
| **`workspace_members`** | Workspace Members | Workspace Owners/Admins | Workspace Owners/Admins | Workspace Owners/Admins |

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

## Phase 3.4 Scan Events And V2 Detections

### 1. Schema Architecture & Relations

We introduce workspace-scoped scan history tracks and advanced detection metadata records.

#### Table: `public.scan_events`
- `id` uuid primary key default `gen_random_uuid()`
- `workspace_id` uuid not null references `public.workspaces(id)` on delete cascade
- `repository_id` uuid references `public.repositories(id)` on delete set null
- `github_delivery_id` text
- `event_type` text not null default `'push'`
- `repo_full_name` text
- `branch` text
- `commit_sha` text
- `status` text not null default `'pending'`
- `error_message` text
- `started_at` timestamptz
- `completed_at` timestamptz
- `created_at` timestamptz not null default `now()`
- `updated_at` timestamptz not null default `now()`
- check constraint `chk_scan_status`: restricts `status` to `pending`, `running`, `completed`, `failed`, `skipped`

#### Table: `public.v2_detections`
- `id` uuid primary key default `gen_random_uuid()`
- `workspace_id` uuid not null references `public.workspaces(id)` on delete cascade
- `repository_id` uuid references `public.repositories(id)` on delete set null
- `scan_event_id` uuid references `public.scan_events(id)` on delete cascade
- `repo_full_name` text
- `branch` text
- `commit_sha` text
- `file_path` text not null
- `line_number` integer
- `secret_type` text not null
- `masked_value` text not null (no raw secrets are ever stored)
- `detection_method` text
- `entropy_score` numeric
- `severity` text not null default `'medium'`
- `confidence_score` numeric
- `ai_reasoning` text
- `ai_recommendation` text
- `status` text not null default `'open'`
- `detected_at` timestamptz not null default `now()`
- `resolved_at` timestamptz
- `created_at` timestamptz not null default `now()`
- `updated_at` timestamptz not null default `now()`
- check constraint `chk_v2_severity`: restricts `severity` to `low`, `medium`, `high`, `critical`
- check constraint `chk_v2_status`: restricts `status` to `open`, `ignored`, `resolved`, `false_positive`

> [!WARNING]
> Storing raw secret values poses a critical security risk. The `v2_detections` table contains only masked previews (`masked_value`) to preserve database confidentiality.

---

### 2. Row-Level Security (RLS) & Access Isolation

RLS is enabled on both `public.scan_events` and `public.v2_detections`.

#### Policy Rules Matrix

| Table | SELECT | INSERT | UPDATE | DELETE |
| :--- | :--- | :--- | :--- | :--- |
| **`scan_events`** | Workspace Members | Workspace Owners/Admins | Workspace Owners/Admins | Workspace Owners/Admins |
| **`v2_detections`** | Workspace Members | Workspace Owners/Admins | Workspace Owners/Admins | Workspace Owners/Admins |

---

## Phase 3.5 RLS Policies And Index Review

All database components defined in Phase 3 have been reviewed and hardened. If `backend/supabase_v2_multi_user_schema.sql` is modified, the SQL must be run manually in the Supabase SQL Editor to apply the changes.

### 1. Hardening & Verification Checklist
- **RLS Status**: Row-Level Security has been explicitly verified and enabled on all 7 V2 tables.
- **Select Isolation**: Workspace membership controls read access. SELECT for all tenant-bound data is restricted to authenticated users verified to be members of the workspace.
- **Write Policies**: Workspace-owned mutation actions (INSERT, UPDATE, DELETE) are restricted to workspace users configured with the role `'owner'` or `'admin'`, validated securely via the recursion-free `is_workspace_admin_or_owner` function. The workspace row itself remains owner-controlled.
- **Privilege Escalation Protection**: Regular members are prevented from writing to `workspace_members`. Admins cannot create, update, or delete owner membership records, which prevents admin-to-owner escalation through membership writes.
- **Cross-Workspace Write Protection**: Repository writes verify the GitHub installation belongs to the same workspace. Scan event and V2 detection writes verify related repositories and scan events remain in the same workspace.
- **Data Security**: Discord webhook URLs remain stored as `webhook_url_ciphertext` only, without a plain `webhook_url` column. V2 detections store `masked_value` only, without raw secrets.

### 2. Performance Index Summary
Indexes were reviewed and added where useful for workspace-scoped ownership, membership, integration, scan, and detection lookup filters.
- `idx_workspaces_owner_user_id` on workspaces.
- `idx_workspace_members_user_id`, `idx_workspace_members_workspace_id`, and `idx_workspace_members_user_workspace_role` on members.
- `idx_github_installations_workspace_id`, `idx_github_installations_installation_id`, and `idx_github_installations_account_login` on installations.
- `idx_repositories_workspace_id`, `idx_repositories_github_installation_id`, `idx_repositories_github_repo_id`, `idx_repositories_full_name`, `idx_repositories_monitoring_enabled`, `idx_repositories_workspace_github_repo_id`, and `idx_repositories_workspace_full_name` on repositories.
- `idx_discord_webhooks_workspace_id`, `idx_discord_webhooks_enabled`, `idx_discord_webhooks_created_by_user_id`, and `idx_discord_webhooks_workspace_enabled` on webhooks.
- `idx_scan_events_workspace_id`, `idx_scan_events_repository_id`, `idx_scan_events_github_delivery_id`, `idx_scan_events_commit_sha`, `idx_scan_events_status`, `idx_scan_events_created_at`, `idx_scan_events_workspace_repository_id`, `idx_scan_events_workspace_github_delivery_id`, `idx_scan_events_workspace_status_created_at`, and `idx_scan_events_workspace_created_at` on scan events.
- `idx_v2_detections_workspace_id`, `idx_v2_detections_repository_id`, `idx_v2_detections_scan_event_id`, `idx_v2_detections_severity`, `idx_v2_detections_status`, `idx_v2_detections_secret_type`, `idx_v2_detections_detected_at`, `idx_v2_detections_commit_sha`, `idx_v2_detections_workspace_repository_id`, `idx_v2_detections_workspace_scan_event_id`, `idx_v2_detections_workspace_severity_status_detected_at`, and `idx_v2_detections_workspace_status_detected_at` on detections.

---

### 3. Non-Implemented Components (Deferred to Phase 4+)

To preserve the stability of the V1 features and control scope progression, the following are intentionally deferred:
- **V1 Detections table** (`detections`) is **not** modified or migrated.
- **Webhook processing** and **scanner logic** remain unchanged.
- **GitHub App oauth callback, tokens, and routing backend APIs** are not yet implemented.

---

## Phase 3.6 Final Verification

Phase 3 has been re-verified as complete and ready for Phase 4 implementation work.

### 1. Final Verification Checklist
- **Tables Verified**: All 7 Phase 3 tables exist in the schema: `workspaces`, `workspace_members`, `github_installations`, `repositories`, `discord_webhooks`, `scan_events`, `v2_detections`.
- **RLS Verified**: RLS is enabled on all 7 Phase 3 tables.
- **Read Isolation Verified**: Workspace membership controls tenant-scoped SELECT access.
- **Write Controls Verified**: Workspace-owned records are writable by owner/admin only; workspace row updates/deletes remain owner-controlled.
- **Privilege Escalation Controls Verified**: `workspace_members` policies prevent regular members from role changes and prevent admins from changing/removing owner-role records.
- **Sensitive Data Shape Verified**: Discord webhook URLs are stored as `webhook_url_ciphertext` only; V2 detections store `masked_value` only.
- **Index Coverage Verified**: Workspace, repository, webhook, scan event, and detection query paths have supporting indexes.
- **Idempotency Verified**: Tables/indexes are created with `if not exists`; policies and triggers are dropped before recreation.

### 2. Final Phase 3 Summary
- **Tables Added**: Multi-user workspace, integration, webhook, scan event, and V2 detection tables are fully present.
- **RLS Strategy**: Membership-scoped reads with owner/admin-gated writes using security definer helper functions to avoid policy recursion and enforce role boundaries.
- **Index Strategy**: Combination of foreign-key indexes, workspace-scoped composite indexes, and status/time indexes to support frequent dashboard and API filters.
- **Security Notes**: Ciphertext-only webhook URL storage and masked-only detection values are enforced at schema shape level; cross-workspace write checks are applied to repository and scan-linked records.
- **V1 Compatibility**: V1 `detections` table remains unchanged.
- **Runtime Compatibility**: Webhook processing and scanner logic remain unchanged.
- **Operational Note**: SQL changes require manual execution in the Supabase SQL Editor.
- **Readiness**: Phase 3 is complete and ready for **Phase 4 GitHub App Integration**.
