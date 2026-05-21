# AI SecureWatch V2 Roadmap

AI SecureWatch V2 turns the current single-deployment monitoring tool into a public-ready, multi-user platform. Version 1 remains the working baseline: FastAPI receives GitHub webhooks, scans added lines for secrets, stores safe detection records in Supabase, sends alert payloads to automation, and exposes dashboard APIs.

V2 uses Supabase for both authentication and database storage. SQLite is not part of the V2 plan.

## Current V1 Assets To Reuse

- FastAPI application shell in `backend/app/main.py`
- Health and webhook routing patterns in `backend/app/routes/`
- GitHub webhook signature verification in `backend/app/utils/signature.py`
- GitHub push payload parsing in `backend/app/utils/github_payload.py`
- GitHub commit diff fetching and added-line extraction in `backend/app/services/github_service.py`
- Regex and entropy scanning in `backend/app/services/scanner_service.py`
- Secret masking in `backend/app/utils/masking.py`
- Gemini risk analysis in `backend/app/services/ai_service.py`
- Supabase REST/SDK storage patterns in `backend/app/services/database_service.py`
- Discord/n8n notification safety pattern in `backend/app/services/n8n_service.py`
- React dashboard components for summary cards, charts, recent detections, and detection tables

## Product Goals

1. Users can sign up, log in, and log out.
2. Users can connect GitHub through a GitHub App.
3. Users can install the GitHub App on selected repositories.
4. Users can manage monitored repositories from the dashboard.
5. Users can add and test their own Discord webhook URL.
6. GitHub push events are matched to the correct installation, repository, and user/workspace.
7. Detections are stored under the correct user/workspace and never expose raw secrets.
8. Dashboard views are scoped to the authenticated user.

## Phase 1: Foundation And Architecture

Status: prepared in this repository.

- Review V1 backend and dashboard structure.
- Identify reusable V1 modules.
- Document V2 backend architecture.
- Document V2 dashboard pages.
- Add non-breaking TODO markers for Supabase Auth, GitHub App, and per-user Discord alerting.
- Keep all V1 runtime behavior unchanged.

## Phase 2: Supabase Auth Foundation

- Status: completed for the V2 auth foundation scope.
- Completed: Supabase Auth client setup for the dashboard.
- Completed: Auth context and session persistence.
- Completed: email/password login page.
- Completed: GitHub OAuth login through Supabase Auth.
- Completed: protected dashboard route.
- Completed: logout button.
- Completed: `profiles` SQL schema linked to Supabase `auth.users` with RLS.
- Completed: backend JWT verification dependency.
- Completed: dashboard API access token attachment.
- Deferred: dedicated email signup UI. GitHub OAuth currently supports sign-in/sign-up through Supabase.
- Deferred: applying JWT protection to existing V1 dashboard APIs. Existing V1 behavior remains unchanged.

## Phase 3: Multi-User Database Schema

- Status: in progress.
- Completed Phase 3.1: Workspaces and workspace_members database schema with RLS, performance indexes, and profile-triggered auto-creation.
- Remaining Phase 3.2+: Add github_installations, repositories, discord_webhooks, scan_events, detections_v2, and RLS policies for them.
- Keep service-role-only backend writes for webhook ingestion.
- Migrate or isolate the V1 `detections` table before changing production data shape.

## Phase 4: GitHub App Integration

- Create a GitHub App for AI SecureWatch.
- Add GitHub App manifest/config documentation.
- Add backend routes for GitHub App installation callbacks.
- Store installation IDs and selected repositories in Supabase.
- Replace the global `GITHUB_TOKEN` commit fetch path with installation access tokens.
- Keep webhook signature verification active.

## Phase 5: Repository Management

- Add dashboard pages for connected GitHub account/installations.
- List installed repositories.
- Allow users to enable or disable monitoring per repository.
- Store repository state in Supabase.
- Add backend APIs for repository list and monitoring settings.

## Phase 6: Per-User Discord Alerts

- Add dashboard settings for Discord webhook URL.
- Store Discord webhook URLs securely in Supabase.
- Add a "send test alert" backend endpoint.
- Route each detection to the owning user/workspace Discord webhook.
- Preserve safe payload behavior: masked values only, no raw secrets.

## Phase 7: Detection Pipeline Upgrade

- Resolve each GitHub webhook to a GitHub installation and repository.
- Fetch diffs using installation access tokens.
- Reuse V1 scanner and AI analysis.
- Store detections with user/workspace/repository ownership.
- Add idempotency for repeated webhook deliveries.
- Add queue/retry design if webhook processing grows beyond FastAPI background tasks.

## Phase 8: Dashboard V2

- Add authenticated app layout and navigation.
- Add pages for overview, detections, repositories, integrations, alert settings, and account settings.
- Scope all dashboard data to the logged-in user.
- Add empty states for new users with no GitHub installation.
- Add onboarding flow for GitHub and Discord setup.

## Phase 9: Public Readiness

- Add error reporting and structured logs.
- Add rate-limit handling for GitHub API calls.
- Add audit/event logs for installations, repository changes, and alert delivery.
- Add privacy/security docs.
- Add production deployment checklist for Render, Vercel, Supabase, GitHub App, and n8n/Discord.
- Add tests for auth, installation mapping, repository scoping, detection storage, and alert routing.

## Phase 10: Launch Hardening

- Validate RLS policies with negative tests.
- Confirm no raw secret values are stored or sent to third parties.
- Add backup/export process for Supabase.
- Add abuse prevention for public signup.
- Add monitoring for webhook failures and alert delivery failures.
