# AI SecureWatch V2 Phase 3: Multi-User Database Schema

This document details the database schema design and Row-Level Security (RLS) structure for **AI SecureWatch V2 Phase 3.1**. The goal of this phase is to establish the foundation for multi-user ownership using workspaces and workspace_members.

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

### 4. Non-Implemented Components (Deferred to Phase 3.2+)

To preserve the stability of the V1 features and control scope progression, the following are intentionally deferred:
- **GitHub App integration** tables (`github_installations`) are not added yet.
- **Monitored repositories** tables (`repositories`) are not added yet.
- **Discord webhooks** settings tables (`discord_webhooks`) are not added yet.
- **Scan events / V2 detections** tables (`scan_events`, `detections_v2`) are not created yet.
- **V1 Detections table** (`detections`) is **not** modified or migrated.
- **Webhook processing** and **scanner logic** remain unchanged.
