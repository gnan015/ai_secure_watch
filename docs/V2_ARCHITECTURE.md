# AI SecureWatch V2 Architecture

## Architecture Principle

V2 should extend the current V1 system without breaking it. The V1 scanner, masking, AI analysis, GitHub diff parsing, and dashboard display components are useful and should remain reusable. New multi-user concerns should be added through clearly separated auth, installation, repository, and alert modules.

## Backend Structure Proposal

The current backend can evolve toward this structure:

```text
backend/
  app/
    main.py
    config.py
    dependencies/
      auth.py
      supabase.py
    routes/
      auth.py
      detections.py
      github_app.py
      health.py
      integrations.py
      repositories.py
      webhook.py
    schemas/
      auth.py
      detection.py
      github.py
      integration.py
      repository.py
      workspace.py
    services/
      ai_service.py
      alert_service.py
      database_service.py
      discord_service.py
      github_app_service.py
      github_service.py
      repository_service.py
      scanner_service.py
      supabase_auth_service.py
      webhook_processor.py
    utils/
      entropy.py
      github_payload.py
      masking.py
      signature.py
    v1/
      legacy_notes.md
```

This is a proposed structure, not a completed migration. Phase 1 intentionally does not move existing V1 files.

## Backend Module Responsibilities

`dependencies/auth.py`

- Verify Supabase Auth JWTs from dashboard requests.
- Return the current authenticated user.
- Keep public webhook routes separate from user-authenticated dashboard routes.

`dependencies/supabase.py`

- Create Supabase clients for anon-authenticated reads and backend service-role operations.
- Keep service role usage backend-only.

`routes/auth.py`

- Optional backend session helper endpoints.
- Most auth UI will use Supabase client in the dashboard.

`routes/github_app.py`

- Handle GitHub App installation callbacks.
- Support installation sync and repository import.

`routes/repositories.py`

- List repositories available to the logged-in user.
- Enable or disable monitoring per repository.

`routes/integrations.py`

- Save/test Discord webhook settings.
- Later support additional alert providers.

`services/github_app_service.py`

- Generate GitHub App JWTs.
- Exchange installation IDs for installation access tokens.
- Fetch installation repositories.

`services/repository_service.py`

- Map GitHub repositories to Supabase repository records.
- Enforce workspace/user ownership.

`services/discord_service.py`

- Send direct Discord webhook alerts for a user's configured webhook.
- Preserve the V1 safe-payload rule.

`services/alert_service.py`

- Decide which alert provider to use for a detection.
- Route detection alerts to the owning workspace.

`services/supabase_auth_service.py`

- Verify and decode Supabase JWTs when backend validation is needed.

## Data Model Proposal

```text
profiles
- id uuid primary key references auth.users(id)
- email text
- display_name text
- created_at timestamptz

workspaces
- id uuid primary key
- owner_user_id uuid references profiles(id)
- name text
- created_at timestamptz

workspace_members
- workspace_id uuid references workspaces(id)
- user_id uuid references profiles(id)
- role text
- created_at timestamptz

github_installations
- id uuid primary key
- workspace_id uuid references workspaces(id)
- installation_id bigint unique
- account_login text
- account_type text
- created_at timestamptz
- updated_at timestamptz

repositories
- id uuid primary key
- workspace_id uuid references workspaces(id)
- github_installation_id uuid references github_installations(id)
- github_repo_id bigint unique
- full_name text
- owner text
- name text
- default_branch text
- monitoring_enabled boolean
- created_at timestamptz
- updated_at timestamptz

discord_webhooks
- id uuid primary key
- workspace_id uuid references workspaces(id)
- webhook_url text
- enabled boolean
- created_at timestamptz
- updated_at timestamptz

scan_events
- id uuid primary key
- workspace_id uuid references workspaces(id)
- repository_id uuid references repositories(id)
- github_delivery_id text
- commit_sha text
- status text
- created_at timestamptz

detections
- id uuid primary key
- workspace_id uuid references workspaces(id)
- repository_id uuid references repositories(id)
- scan_event_id uuid references scan_events(id)
- repo_full_name text
- branch text
- commit_sha text
- file_path text
- line_number integer
- secret_type text
- masked_value text
- detection_method text
- entropy_score numeric
- severity text
- confidence_score numeric
- ai_reasoning text
- ai_recommendation text
- status text
- detected_at timestamptz
- resolved_at timestamptz
```

Raw secret values must not be stored in any V2 table.

## Webhook Processing Flow

1. GitHub sends a push event to `/webhook/github`.
2. Backend verifies GitHub webhook signature.
3. Backend extracts installation ID and repository ID from payload.
4. Backend finds the matching workspace and repository in Supabase.
5. Backend ignores the event if monitoring is disabled.
6. Backend creates a scan event record.
7. Backend fetches commit diffs using a GitHub App installation token.
8. Backend extracts added lines with file paths and line numbers.
9. Backend reuses V1 scanner and AI analysis.
10. Backend stores masked detections under the correct workspace.
11. Backend sends a Discord alert through the user's configured webhook.

## Dashboard Pages Proposal

- `/login`: sign in with Supabase Auth.
- `/signup`: create a new account.
- `/onboarding`: guide new users through GitHub and Discord setup.
- `/dashboard`: overview cards, charts, and recent detections.
- `/detections`: searchable/filterable detection table.
- `/repositories`: installed repositories and monitoring toggles.
- `/integrations/github`: GitHub App install/sync status.
- `/integrations/discord`: Discord webhook setup and test alert.
- `/settings/account`: profile, email, sign out.
- `/settings/workspace`: workspace name and member settings for later team support.

## Security Boundaries

- Supabase Auth handles user identity.
- Supabase RLS scopes dashboard reads/writes to the current user/workspace.
- Backend service role handles trusted webhook writes.
- GitHub webhook signature verification remains mandatory.
- GitHub App installation tokens replace broad personal access tokens.
- Discord webhook URLs are user/workspace settings and must not be exposed to other users.
- Raw secrets are masked before storage and alerting.

## V1 Compatibility Notes

- Keep existing `/health`, `/webhook/github`, and `/api/*` routes working during V2 buildout.
- Do not change V1 dashboard API response shapes until the V2 dashboard is ready.
- Introduce V2 tables and APIs beside existing V1 behavior before migrating.
- Keep `backend/supabase_schema.sql` as the V1 schema until a V2 migration file is added.
