# AI SecureWatch V2 Phase 10 Launch Hardening

Phase 10 focuses on final safety checks before public launch. Phase 10.1 is limited to access-boundary negative tests and API leak checks; it does not change scanner rules, webhook processing behavior, V1 detections, billing, or dashboard design.

## Phase 10.1 Launch Safety Audit And Negative Access Tests

Status: completed.

Completed:

- Added mocked negative access tests for workspace-scoped V2 detections, scan events, repositories, Discord webhooks, and GitHub installation repository sync.
- Verified own V2 detection status updates can succeed and other-workspace detection updates fail with `404`.
- Verified invalid V2 detection status updates fail with `400`.
- Verified own repository monitoring updates can succeed and other-workspace repository updates fail with `404`.
- Verified own Discord webhook list, create, update, delete, and test actions return safe response payloads.
- Verified other-workspace Discord webhook update, delete, and test actions fail with `404`.
- Verified GitHub installation repository sync cannot proceed when the installation is not saved to the authenticated user's workspace.
- Added recursive sensitive leak assertions around API/service responses touched by Phase 10.1 tests.

Sensitive values checked:

- Supabase service role key
- Supabase JWT secret
- GitHub App private key
- GitHub installation token
- Discord webhook URL
- Discord webhook ciphertext
- Raw secret values
- Authorization headers

Safety notes:

- V2 detections and scan events are returned through explicit safe field allowlists.
- Discord webhook management routes keep raw webhook URLs backend-only; user-facing responses return only `webhook_url_last4`.
- Repository APIs scope reads and updates through the authenticated user's owned workspace.
- GitHub installation sync checks the authenticated user's workspace before listing installation repositories.
- V1 scanner, fallback routing, and V1 detection storage remain unchanged.

Remaining manual launch checks:

- Run live Supabase RLS negative checks with two real users/workspaces before public launch.
- Confirm production environment variables are present only in backend hosting secrets.
- Confirm production logs do not include request bodies, Authorization headers, webhook URLs, installation tokens, or raw secret values.
- Confirm Discord test alerts still work from the production backend after deploy.

## Phase 10.2 Abuse Prevention And Operational Checks

Status: completed.

Lightweight abuse-prevention checks:

- Public signup risk: keep Supabase Auth provider settings reviewed before public launch; disable providers not in use, require email confirmation where appropriate, and monitor sudden profile/workspace creation spikes.
- GitHub webhook spam: webhook requests remain signature-verified before JSON processing or scan work is queued.
- Repeated duplicate deliveries: V2 push deliveries reuse `github_delivery_id` and skip existing `running` or `completed` scan events without queueing processors.
- Discord test alert spam: test alerts remain authenticated and workspace-scoped; disabled webhook records now fail before any outbound Discord request is sent.
- Excessive repository sync calls: installation repository listing uses GitHub pagination with page size 100 and should be monitored for repeated manual sync attempts.
- Large push payloads: current launch posture is documented monitoring rather than broad request rejection, to avoid changing V1 fallback behavior. Watch Render request size/timeouts and GitHub delivery failure reasons.
- GitHub API rate limits: repository sync is paginated; review GitHub API status codes in Render logs and avoid repeated manual sync retries during rate-limit windows.
- Gemini/API cost control: V2 processing only runs for monitored repositories, duplicate deliveries are skipped, and scanner/AI behavior is unchanged for this phase.

Code guardrails added:

- `list_installation_repositories` fetches all repositories available to the GitHub App installation using pagination.
- Discord webhook test rejects disabled webhook records before decrypting/sending.
- Existing V2 dashboard API list limits remain capped at 100 by FastAPI query validation and service-layer clamping.
- Existing duplicate-delivery logic remains idempotent for `running` and `completed` scan events.

Operational checklist:

- Review Render logs daily during launch for `github_webhook_invalid_signature`, `github_webhook_v2_lookup_failed`, `v2_scan_failed`, and Discord test failures.
- Review GitHub App delivery failures in GitHub App settings, especially repeated 401, 400, 500, or timeout responses.
- Review Supabase table growth for `scan_events`, `v2_detections`, `repositories`, `github_installations`, and `discord_webhooks`.
- Review Discord webhook `last_error` and `last_tested_at` fields for repeated failures.
- Monitor webhook failure volume and compare it with GitHub App delivery history.
- Keep a Supabase backup/export reminder before public launch and before any schema change.
- Review environment variables in Render, Vercel, Supabase, and GitHub App settings; remove unused secrets and confirm backend-only secrets are not exposed to the dashboard.
- Safe incident response checklist: pause public signup if abuse appears, disable affected GitHub App installation if needed, rotate exposed third-party credentials, preserve relevant delivery IDs and scan event IDs, review safe logs, and document remediation without copying raw secrets.

Tests added:

- FastAPI endpoint tests verify V2 dashboard `limit > 100` is rejected.
- FastAPI endpoint tests verify invalid V2 filters return `400`.
- FastAPI endpoint test verifies Discord test endpoint requires authentication.
- FastAPI endpoint test verifies disabled Discord webhook tests do not send outbound messages.
- Service test verifies GitHub installation repository sync paginates until GitHub returns a short page.

## Phase 10.3 Final Launch Checklist

Status: completed.

Final backend deployment checklist:

- Deploy the backend with `APP_ENV=production`.
- Set `FRONTEND_URL` to the deployed dashboard origin.
- Configure backend secrets only in Render or the backend hosting provider.
- Confirm `/health` returns healthy after deploy.
- Confirm `/webhook/github` rejects invalid signatures and accepts valid GitHub App push deliveries.
- Confirm protected `/api/*` V2 routes require Supabase Bearer auth.
- Confirm Render logs contain only safe structured metadata.

Final dashboard deployment checklist:

- Configure only public dashboard variables: `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, and `VITE_SUPABASE_ANON_KEY`.
- Confirm no service role key, JWT secret, GitHub App private key, Discord encryption key, or webhook URL is present in dashboard env.
- Run `npm.cmd run build`.
- Verify `/login`, `/dashboard`, `/repositories`, `/integrations/discord`, `/scan-events`, and `/detections`.
- Confirm logged-out users are redirected to `/login`.

Final Supabase checklist:

- Confirm V2 schema is applied.
- Confirm RLS is enabled on V2 tables.
- Confirm workspace isolation is enforced for `workspaces`, `workspace_members`, `github_installations`, `repositories`, `discord_webhooks`, `scan_events`, and `v2_detections`.
- Confirm `v2_detections` stores `masked_value` and no raw secret field.
- Confirm `discord_webhooks` stores ciphertext and last-four display data only.
- Confirm backup/export process is ready before public launch.
- Monitor table growth during beta.

Final GitHub App checklist:

- Confirm webhook URL points to the deployed backend `/webhook/github`.
- Confirm GitHub webhook secret matches backend `GITHUB_WEBHOOK_SECRET`.
- Confirm GitHub App private key is backend-only.
- Confirm permissions include required read-only metadata/content access and push events.
- Confirm installation save and repository sync work.
- Confirm duplicate delivery redelivery is skipped without duplicate scan events or detections.
- Review GitHub App delivery failures after deploy.

Final Discord checklist:

- Confirm Discord webhook URL saves encrypted at rest.
- Confirm dashboard displays only masked webhook last-four data.
- Confirm test alert works for an enabled workspace-owned webhook.
- Confirm disabled webhook test requests fail before sending.
- Confirm detection alerts include masked values only.
- Review `last_tested_at` and `last_error` for repeated failures.

Final security checklist:

- Service role key is backend-only.
- GitHub App private key is backend-only.
- JWT secret is backend-only.
- Discord encryption key is backend-only.
- No secrets are in dashboard env.
- CORS production `FRONTEND_URL` is correct.
- RLS is enabled on V2 tables.
- Workspace isolation is verified.
- Negative tests pass.
- Raw secrets are not stored, logged, displayed, or sent to Discord.
- Authorization headers and installation tokens are not logged or returned by APIs.

Final manual smoke test checklist:

- Login with GitHub.
- Install GitHub App.
- Sync repositories.
- Toggle monitoring.
- Save/test Discord webhook.
- Push fake secret.
- Confirm `scan_events` row created.
- Confirm `v2_detections` row created.
- Confirm Discord alert sent.
- Confirm `/dashboard` overview updates.
- Confirm `/scan-events` shows scan.
- Confirm `/detections` shows masked detection.
- Confirm detection status update works.
- Confirm raw secret is not stored, logged, or displayed.

Final rollback checklist:

- Keep the previous backend deploy available for rollback.
- Keep the previous dashboard deploy available for rollback.
- If webhook processing misbehaves, disable the GitHub App webhook or affected installation before investigating.
- If dashboard auth/API behavior breaks, roll back the dashboard first when backend health and API checks are passing.
- If database issues appear, pause public signup and avoid schema changes until backup/export status is confirmed.
- Preserve delivery IDs, scan event IDs, and safe logs for investigation.

Final incident response checklist:

- Pause public signup or limit beta access if abuse appears.
- Disable affected GitHub App installation or webhook if repeated abusive deliveries occur.
- Rotate any potentially exposed third-party credential immediately.
- Review Render logs, GitHub App delivery history, Supabase table activity, and Discord webhook errors.
- Do not copy raw secrets into tickets, docs, chat, or logs.
- Document impact, timeline, mitigation, and follow-up actions using only safe metadata.

Final known limitations:

- No billing/subscriptions yet.
- No advanced rate limiting yet.
- No organization/team management UI yet.
- V1 fallback still exists.
- Dashboard is functional but can be visually improved later.
- Public launch should start with limited beta users.
