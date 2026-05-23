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

- Status: completed.
- Completed Phase 3.1: Workspaces and workspace_members database schema with RLS, performance indexes, and profile-triggered auto-creation.
- Completed Phase 3.2: GitHub Installations and Repositories database schema with RLS, helper policies for owners/admins, and performance indexes.
- Completed Phase 3.3: Discord Webhooks database schema with ciphertext storage, RLS, and performance indexes.
- Completed Phase 3.4: Scan Events and V2 Detections database schema with RLS, check constraints, and performance indexes.
- Completed Phase 3.5: Full RLS policy review and hardening across all 7 V2 tables. Inline policy intent comments added. Privilege escalation and cross-workspace write protection verified. Index coverage confirmed.
- Completed Phase 3.6: Final Phase 3 verification and documentation cleanup. Confirmed schema completeness, RLS coverage, index coverage, idempotent SQL shape, and Phase 4 readiness.
- Keep service-role-only backend writes for webhook ingestion.
- Migrate or isolate the V1 `detections` table before changing production data shape.

## Phase 4: GitHub App Integration

- Status: completed.
- Completed Phase 4.1: GitHub App setup and configuration documentation, required permissions/events, required app settings, backend env placeholders, and manual setup checklist.
- Completed Phase 4.2: GitHub App backend service added for app JWT generation, installation access token generation, installation metadata fetch, and authenticated installation save API to `github_installations`.
- Completed Phase 4.3: Protected repository sync API added to fetch installation repositories and upsert them into `public.repositories` without duplication.
- Completed Phase 4.4: Final Phase 4 verification and docs cleanup. Confirmed installation save and repository sync readiness and preserved V1 webhook/scanner behavior.
- Create a GitHub App for AI SecureWatch.
- Add GitHub App manifest/config documentation.
- Add backend routes for GitHub App installation callbacks.
- Store installation IDs and selected repositories in Supabase.
- Replace the global `GITHUB_TOKEN` commit fetch path with installation access tokens.
- Keep webhook signature verification active.

## Phase 5: Repository Management

- Status: completed.
- Completed Phase 5.1: Protected backend repository APIs added to list workspace repositories and update `monitoring_enabled` with workspace ownership checks.
- Completed Phase 5.2: Protected dashboard repositories page added with repository list and monitoring toggle using Phase 5.1 APIs.
- Completed Phase 5.3: Final Phase 5 verification and documentation cleanup for repository management readiness.
- Add dashboard pages for connected GitHub account/installations.
- List installed repositories.
- Allow users to enable or disable monitoring per repository.
- Store repository state in Supabase.
- Add backend APIs for repository list and monitoring settings.

## Phase 6: Per-User Discord Alerts

- Status: completed.
- Completed Phase 6.1: Protected backend Discord webhook management APIs added with encrypted webhook URL storage, workspace ownership checks, and backend-side test message sending.
- Completed Phase 6.2: Protected dashboard Discord settings page added with create/list/update/delete/test controls using Phase 6.1 APIs and masked webhook display.
- Completed Phase 6.3: Final Phase 6 verification and documentation cleanup for per-user Discord alerts foundation readiness.
- Add dashboard settings for Discord webhook URL.
- Store Discord webhook URLs securely in Supabase.
- Add a "send test alert" backend endpoint.
- Route each detection to the owning user/workspace Discord webhook.
- Preserve safe payload behavior: masked values only, no raw secrets.

## Phase 7: Detection Pipeline Upgrade

- Status: next.
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
