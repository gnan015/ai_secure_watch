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
