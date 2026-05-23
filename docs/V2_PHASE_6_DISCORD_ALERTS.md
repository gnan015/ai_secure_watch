# AI SecureWatch V2 Phase 6: Per-User Discord Alerts

## Phase 6.1 Backend Discord Webhook APIs

Phase 6.1 adds protected backend APIs for workspace-scoped Discord webhook management with encrypted storage.

### Added Endpoints
- `GET /api/discord/webhooks`
- `POST /api/discord/webhooks`
- `PATCH /api/discord/webhooks/{webhook_id}`
- `DELETE /api/discord/webhooks/{webhook_id}`
- `POST /api/discord/webhooks/{webhook_id}/test`

### Security And Ownership
- All endpoints require Supabase auth (`Authorization: Bearer <token>`).
- Webhook records are scoped to the authenticated user's owned workspace.
- Access to webhook rows outside the user's workspace is denied.

### Encrypted Storage Rules
- Raw Discord webhook URLs are never stored in Supabase.
- Raw Discord webhook URLs are never returned from API responses.
- URLs are stored only as:
  - `webhook_url_ciphertext`
  - `webhook_url_last4`
- Encryption/decryption uses Fernet with:
  - `DISCORD_WEBHOOK_ENCRYPTION_KEY`

### Test Message Behavior
- `POST /api/discord/webhooks/{webhook_id}/test` decrypts the webhook URL on backend only.
- Sends a safe test message to Discord.
- Updates webhook metadata (`last_tested_at`, `last_error`) without exposing raw URLs.

### Scope Notes
- V1 `/webhook/github` behavior is unchanged.
- V1 scanner logic is unchanged.
- V1 alert flow remains unchanged in this phase.
- Dashboard Discord settings UI is deferred to Phase 6.2.

---

## Phase 6.2 Dashboard Discord Settings Page

Phase 6.2 adds dashboard UI for authenticated users to manage workspace Discord webhook settings.

### What Was Added
- Protected dashboard route:
`/integrations/discord`
- Discord settings page with:
  - loading state
  - error state
  - empty state
  - saved webhook list
  - create form (name + webhook URL)
  - webhook actions: enable/disable, test, delete

### API Usage
- `GET /api/discord/webhooks`
- `POST /api/discord/webhooks`
- `PATCH /api/discord/webhooks/{webhook_id}`
- `DELETE /api/discord/webhooks/{webhook_id}`
- `POST /api/discord/webhooks/{webhook_id}/test`

### Sensitive Data Handling
- Raw webhook URL is entered only during create/update actions.
- Raw webhook URL is never displayed after save.
- Dashboard shows masked webhook info via `webhook_url_last4` only.
- `webhook_url_ciphertext` is never displayed in UI.

### Scope Notes
- Real detection alert routing to per-user Discord webhook is deferred to later phase work.
- V1 webhook/scanner behavior is unchanged.

---

## Phase 6.3 Final Phase 6 Verification

Phase 6 Per-User Discord Alerts foundation is complete and ready for Phase 7.

### What Phase 6 Added
- Workspace-scoped backend Discord webhook management APIs.
- Fernet-encrypted Discord webhook URL storage.
- Protected dashboard Discord settings page for create/list/update/delete/test operations.

### Endpoints Added
- `GET /api/discord/webhooks`
- `POST /api/discord/webhooks`
- `PATCH /api/discord/webhooks/{webhook_id}`
- `DELETE /api/discord/webhooks/{webhook_id}`
- `POST /api/discord/webhooks/{webhook_id}/test`

### Dashboard Route Added
- Protected route:
`/integrations/discord`

### Required Environment Variable
- `DISCORD_WEBHOOK_ENCRYPTION_KEY`

### Manual Test Checklist
- `npm run build` passes in `dashboard`.
- Logged-out users are redirected from `/integrations/discord` to `/login`.
- Logged-in users can create/list/update/delete/test Discord webhooks.
- No-auth backend Discord endpoints return `401`.
- Webhook list returns masked fields only (such as `webhook_url_last4`).
- Raw webhook URL is not returned from backend responses.
- Raw webhook URL is not displayed after save in dashboard UI.
- Test endpoint sends a safe Discord test message and updates `last_tested_at` / `last_error`.
- `/dashboard` and `/repositories` continue to work.
- `/health` remains public.
- `/webhook/github` remains public and unchanged.

### Security Notes
- Webhook URL values are encrypted before database storage.
- `webhook_url_ciphertext` is never displayed in frontend UI.
- Raw webhook URL is entered only during create/update and never shown later.
- Workspace ownership checks are enforced for all Discord webhook operations.

### Intentionally Not Implemented In Phase 6
- Routing real detection alerts to per-user Discord webhooks in production detection flow.
- Detection pipeline upgrade changes.
- Scanner/webhook flow redesign.
- V1 detections migration.

### Readiness
- Phase 6 is complete and ready for **Phase 7 Detection Pipeline Upgrade**.
