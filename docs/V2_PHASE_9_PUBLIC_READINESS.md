# AI SecureWatch V2 Phase 9: Public Readiness

## Phase 9.1 Production Readiness And Deployment Audit

Phase 9.1 verifies deployment configuration, environment requirements, dependency manifests, and production checklists before deeper public-readiness hardening.

### Render Backend Deployment Checklist

- Deploy the `backend` service from the repository root or backend service directory expected by Render.
- Use the backend start command from the deployment target, such as `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Configure all backend environment variables in Render; do not rely on committed `.env` files.
- Confirm `/health` is public and returns healthy status after deploy.
- Confirm `/webhook/github` is public and rejects invalid signatures.
- Confirm protected `/api/*` routes require Supabase Bearer auth.
- Confirm backend logs do not print raw secret values, service role keys, GitHub private keys, JWT secrets, or webhook URLs.

### Dashboard Deployment Checklist

- Configure `VITE_API_BASE_URL` to the deployed backend URL.
- Configure `VITE_SUPABASE_URL`.
- Configure `VITE_SUPABASE_ANON_KEY`.
- Keep service-role and private backend secrets out of frontend deployment settings.
- Build with `npm run build`.
- Verify `/login`, `/dashboard`, `/repositories`, `/integrations/discord`, `/scan-events`, and `/detections`.
- Verify logged-out users are redirected to `/login` for protected dashboard routes.

### Supabase Setup Checklist

- Apply the V2 multi-user schema in `backend/supabase_v2_multi_user_schema.sql`.
- Confirm RLS is enabled on V2 tables.
- Confirm authenticated users can only read/write workspace-scoped rows through policies.
- Confirm backend service-role key is available only in backend environment variables.
- Confirm `github_installations`, `repositories`, `scan_events`, and `v2_detections` exist.
- Confirm `discord_webhooks` stores encrypted webhook URLs only.
- Confirm `v2_detections` stores `masked_value` and has no raw secret column.

### GitHub App Setup Checklist

- GitHub App webhook URL points to the deployed backend `/webhook/github`.
- GitHub App webhook secret matches backend `GITHUB_WEBHOOK_SECRET`.
- GitHub App ID is set in backend `GITHUB_APP_ID`.
- GitHub App private key is set in backend `GITHUB_APP_PRIVATE_KEY`.
- GitHub App has `Metadata: Read-only` and `Contents: Read-only`.
- GitHub App subscribes to `Push` events.
- Installation is saved to `github_installations`.
- Repositories are synced to `repositories`.
- Target repositories have `monitoring_enabled=true`.

### Environment Variable Checklist

Backend:

- `APP_NAME`
- `APP_ENV`
- `FRONTEND_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `GITHUB_WEBHOOK_SECRET`
- `GITHUB_TOKEN` for V1 fallback while still enabled
- `GITHUB_APP_ID`
- `GITHUB_APP_PRIVATE_KEY`
- `GITHUB_APP_WEBHOOK_SECRET`
- `GITHUB_APP_CLIENT_ID`
- `GITHUB_APP_CLIENT_SECRET`
- `DISCORD_WEBHOOK_ENCRYPTION_KEY`
- `GEMINI_API_KEY`
- `N8N_WEBHOOK_URL` for V1 alert flow while still enabled

Dashboard:

- `VITE_API_BASE_URL`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

### Webhook Secret Checklist

- GitHub App webhook secret and backend `GITHUB_WEBHOOK_SECRET` must match.
- Invalid signatures must return `401`.
- Missing signature must return `401`.
- Valid signed push webhook must route by `installation.id` and `repository.id`.
- Unknown installation/repository should preserve V1 fallback behavior.

### Live V2 Ingestion Verification Checklist

- Real GitHub App push creates a `scan_events` row.
- Real fake-secret push creates a `v2_detections` row.
- `scan_events.status` becomes `completed` after successful processing.
- Insert failure marks `scan_events.status=failed` with safe error text.
- Duplicate delivery does not create duplicate scan events or detections.
- `v2_detections.masked_value` is populated.
- Raw secret values are not stored.
- Dashboard `/scan-events` shows the scan event.
- Dashboard `/detections` shows the detection.

### Discord Alert Verification Checklist

- Discord webhook URL is encrypted at rest.
- Dashboard displays only webhook last-four masking.
- Test message endpoint works for configured webhook.
- Detection alert payload contains masked values only.
- No raw secrets are sent in alert payloads.

### Dashboard Verification Checklist

- `/login` works for Supabase Auth.
- `/dashboard` loads V2 overview cards.
- `/repositories` lists synced repositories and monitoring status.
- `/integrations/discord` manages workspace Discord webhooks.
- `/scan-events` lists recent V2 scan events.
- `/detections` lists V2 detections and supports status updates.
- Dashboard API calls include Supabase Bearer token.
- No raw secret fields are requested or displayed.

### Security Notes

- Supabase service role key must never be exposed to the frontend.
- GitHub App private key must never be exposed to the frontend.
- Supabase JWT secret must never be exposed to the frontend.
- Discord encryption key must never be exposed to the frontend.
- Raw secrets must never be stored in Supabase.
- Raw secrets must never be sent to Discord, n8n, browser responses, or logs.
- GitHub webhook signature verification must remain enabled.
- `/health` remains public; protected dashboard APIs remain auth-gated.

### Phase 9.1 Readiness

Phase 9.1 is complete for deployment audit documentation. Live V2 ingestion is verified: real GitHub App pushes create `scan_events`, real detected fake secrets create `v2_detections`, Discord alerts are sent, and dashboard pages can show detections.

## Phase 9.2 Logging, Errors, And Security Hardening

Phase 9.2 improves backend safety around logs, errors, CORS, and validation without changing scanner rules, webhook behavior, or V1 fallback behavior.

### Safe Structured Logging

- Added structured safe logging for GitHub webhook signature failures, ignored events, V2 lookup failures, unknown V2 repositories, duplicate deliveries, queued V2 scans, V2 scan start, V2 detection counts, V2 scan completion, and V2 scan failure.
- Safe logs include metadata such as `event_type`, `delivery_id`, `installation_id`, `github_repo_id`, `repo_full_name`, `workspace_id`, `repository_id`, `scan_event_id`, `status`, and detection counts.
- Logs must never include raw secret values, Discord webhook URLs, GitHub App private keys, service role keys, JWT secrets, access tokens, or authorization headers.

### Safe Webhook Errors

- Invalid GitHub webhook signatures return `401` with a clear safe error message.
- Unknown GitHub App installation/repository mappings are logged safely and still preserve V1 fallback behavior.
- Duplicate V2 deliveries return a safe duplicate response.
- V2 processor failures mark the related `scan_event` as `failed` with safe error metadata.

### API Error Consistency

- Auth failures remain `401`.
- Missing workspace-owned detections remain `404`.
- Invalid V2 dashboard filters return `400`.
- Unexpected database/API failures return safe `500` responses without secret details.

### CORS And Security Notes

- Production CORS is limited to `FRONTEND_URL`.
- Development keeps local Vite origins available for local testing.
- `/health` remains public.
- `/webhook/github` remains public and signature-protected.
- Protected dashboard APIs remain Supabase Bearer auth gated.

### V1 Compatibility

- V1 scanner rules are unchanged.
- V1 detection storage is unchanged.
- V1 alert flow is unchanged.
- Unknown V2 repositories still fall back to the existing V1 webhook path.

Phase 9.2 is complete and ready for Phase 9.3 final Phase 9 testing/docs.

## Phase 9.3 Final Phase 9 Verification

Phase 9.3 closes the Public Readiness phase by verifying that deployment documentation, logging/error hardening, security guardrails, and V2 ingestion readiness are aligned with the current implementation.

### What Phase 9 Added

- Production deployment readiness checklists for the backend, dashboard, Supabase, GitHub App, environment variables, webhooks, V2 ingestion, Discord alerts, and dashboard verification.
- Safe structured logging for webhook routing and V2 scan processing metadata.
- Safer webhook errors for invalid signatures, unknown V2 repository mappings, duplicate deliveries, and V2 processor failures.
- V2 dashboard API filter validation for invalid status and severity values.
- Production CORS behavior limited to `FRONTEND_URL`, with localhost origins preserved for development.

### Production Readiness Checklist Summary

- Backend production environment variables are documented.
- Dashboard production environment variables are documented.
- Render backend deployment steps are documented.
- Dashboard deployment steps are documented.
- Supabase setup and table requirements are documented.
- GitHub App permissions, webhook, installation, and repository sync requirements are documented.
- Live V2 ingestion, Discord alerting, and dashboard verification checklists are documented.

### Logging And Security Hardening Summary

- Logs are structured and limited to safe metadata such as delivery ID, event type, repository IDs, workspace/repository IDs, scan event ID, status, and counts.
- Logs must never include raw secrets, Discord webhook URLs, GitHub App private keys, service role keys, JWT secrets, access tokens, or authorization headers.
- API errors return safe messages without internal secret details.
- `/health` remains public.
- `/webhook/github` remains public and signature-protected.
- V2 dashboard APIs remain Supabase Bearer auth protected.

### Live V2 Ingestion Status

Live V2 ingestion is verified: real GitHub App pushes create `scan_events`, real detected fake secrets create `v2_detections`, Discord alerts are sent, and dashboard pages can show detections. Stored and displayed detection records use `masked_value`; raw secret values are not stored, returned, displayed, or logged.

### Deployment Checklist Before Public Release

- Deploy backend with production `APP_ENV=production` and `FRONTEND_URL` set to the deployed dashboard origin.
- Configure all backend secrets in the backend hosting provider only.
- Configure only public dashboard variables in the dashboard hosting provider.
- Verify GitHub App webhook delivery succeeds against the deployed `/webhook/github` endpoint.
- Verify invalid GitHub webhook signatures are rejected.
- Verify Supabase RLS policies are active on V2 tables.
- Verify dashboard auth works with the deployed Supabase project.
- Verify a live fake-secret push creates a completed scan event and masked V2 detection.
- Verify Discord test and detection alerts use masked values only.

### Remaining Manual Checks Before Public Release

- Re-run one production GitHub App webhook delivery after every deploy.
- Confirm production logs contain only safe metadata.
- Confirm frontend build settings do not contain service role keys, private keys, JWT secrets, or Discord encryption keys.
- Confirm old V1 webhook fallback still works for unknown V2 repositories while V1 remains enabled.

### Phase 9 Readiness

Phase 9 is complete for Public Readiness. The project is ready for Phase 10 Launch Hardening, focused on final RLS negative testing, backup/export planning, public signup abuse prevention, and production monitoring.
