# AI SecureWatch V2 Phase 4: GitHub App Integration

Phase 4 introduces GitHub App-based repository access for workspace-scoped monitoring. This document covers setup and configuration for **Phase 4.1 only**.

## Phase 4.1 GitHub App Setup And Config

### Purpose Clarification
- Supabase GitHub OAuth is used for user authentication and login experience only.
- The AI SecureWatch GitHub App is used for repository access, installation mapping, and monitoring authorization.
- Users will install the AI SecureWatch GitHub App on all repositories or selected repositories.
- Each installation provides an `installation_id` and repository access scope used later in backend integration.

### Required GitHub App Permissions And Events
- Repository permissions:
`Metadata: Read-only`
- Repository permissions:
`Contents: Read-only`
- Subscribe to events:
`Push`

### Required GitHub App Settings
- App name:
`AI SecureWatch`
- Homepage URL:
`<dashboard_frontend_url>`
- Webhook URL:
`https://YOUR_BACKEND_DOMAIN/webhook/github`
- Webhook secret:
Store in backend environment as `GITHUB_APP_WEBHOOK_SECRET`
- Callback URL (placeholder for later backend flow):
`https://YOUR_BACKEND_DOMAIN/auth/github-app/callback`

### Backend Environment Variables (Phase 4.1 Prep)
Add these placeholders to backend environment configuration (no real secrets in repo):
- `GITHUB_APP_ID=`
- `GITHUB_APP_PRIVATE_KEY=`
- `GITHUB_APP_WEBHOOK_SECRET=`
- `GITHUB_APP_CLIENT_ID=`
- `GITHUB_APP_CLIENT_SECRET=`

### Manual Setup Checklist
1. Create a new GitHub App in GitHub Developer Settings.
2. Set the GitHub App webhook URL to `https://YOUR_BACKEND_DOMAIN/webhook/github`.
3. Set and save the webhook secret.
4. Enable the `Push` webhook event subscription.
5. Set repository permissions: `Metadata: Read-only` and `Contents: Read-only`.
6. Generate a private key for the GitHub App and store it securely.
7. Copy the GitHub App ID from app settings.
8. Save all GitHub App values in backend `.env` during deployment setup (do not commit secrets).

### Scope Boundaries For Phase 4.1
Not implemented in this phase:
- GitHub App backend routes or installation callback handlers.
- GitHub App JWT generation or installation token exchange.
- Repository fetch/sync logic.
- Changes to webhook processing, scanner logic, dashboard UI, or V1 detections.

---

## Phase 4.2 GitHub App Backend Service And Installation Save API

Phase 4.2 adds backend support for GitHub App authentication and saving installation ownership to Supabase.

### Implemented In Phase 4.2
- GitHub App JWT generation added (`RS256`, issuer=`GITHUB_APP_ID`, short-lived token window).
- GitHub App installation access token generation added for `installation_id`.
- GitHub App installation metadata fetch added.
- Protected backend API added: `POST /api/github/installations`.
- Authenticated users can save an installation to Supabase `github_installations` for their owned workspace.
- Service-role-backed Supabase helpers were added for owned workspace lookup and installation upsert.

### Deferred To Phase 4.3
- Repository synchronization and selected repository persistence are deferred.

### Compatibility Notes
- V1 webhook endpoint behavior is unchanged.
- V1 scanner logic is unchanged.
- V1 detections table remains unchanged.

---

## Phase 4.3 Repository Sync

Phase 4.3 adds backend repository sync for a saved GitHub App installation.

### Implemented In Phase 4.3
- Protected API added: `POST /api/github/installations/{installation_id}/sync-repositories`.
- Backend can fetch repositories accessible to the selected installation.
- Repository records are upserted into Supabase `public.repositories`.
- Repeated sync avoids duplication through upsert keyed by `github_repo_id`.
- `monitoring_enabled` remains defaulted to `true` from schema behavior.

### Scope Notes
- No repository deletion/pruning was added in this phase; sync is upsert-only.
- Dashboard repository UI comes later.
- V1 webhook/scanner behavior remains unchanged.

---

## Phase 4.4 Final Phase 4 Verification

Phase 4 is verified complete for GitHub App integration readiness.

### What Phase 4 Added
- GitHub App configuration documentation and environment variable requirements.
- Backend GitHub App JWT generation (`RS256`) and installation access token exchange.
- Installation metadata fetch from GitHub.
- Protected installation save endpoint:
`POST /api/github/installations`
- Protected repository sync endpoint:
`POST /api/github/installations/{installation_id}/sync-repositories`
- Repository upsert flow into `public.repositories` with idempotent sync behavior.

### Manual Setup Required
- GitHub App must be created in GitHub Developer Settings.
- Webhook URL and webhook secret must be configured.
- Required permissions/events must be configured (`Metadata: Read-only`, `Contents: Read-only`, `Push`).
- App private key and app ID must be set in backend environment variables.

### Successful Integration Result
- `installation_id`: `134901546`
- Repository synced: `gnan015/ai-securewatch-test-repo`

### Intentionally Not Implemented In Phase 4
- GitHub App installation callback route/web UX flow.
- Repository dashboard UI and repository settings screens.
- Repository delete/prune behavior during sync.
- V1 webhook/scanner pipeline changes.
- V1 detections migration.

### Readiness
- Phase 4 is complete and ready for **Phase 5 Repository Management**.
