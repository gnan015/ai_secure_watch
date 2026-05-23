# AI SecureWatch V2 Phase 7: Detection Pipeline Upgrade

## Phase 7.1 GitHub App Webhook Routing

Phase 7.1 adds the routing foundation for GitHub App push webhooks without changing scanner or detection storage behavior.

- `/webhook/github` still verifies the GitHub signature before reading or routing webhook payloads.
- Push webhooks now recognize GitHub App payload fields from `installation.id`, `repository.id`, `repository.full_name`, `X-GitHub-Event`, and `X-GitHub-Delivery`.
- The backend maps `installation_id` + `repo_id` to the workspace-owned V2 repository in Supabase.
- Repository `monitoring_enabled` is respected. Disabled repositories are skipped safely.
- Matched and enabled V2 repositories route into the V2 scan event and detection storage path added in Phase 7.2.
- Existing V1 webhook behavior is preserved for payloads that do not resolve to a V2 repository.

## Phase 7.2 V2 Scan Event And Detection Storage

Phase 7.2 upgrades the monitored GitHub App webhook path to create V2 scan records and store masked V2 detections.

- Monitored GitHub App push webhooks create `public.scan_events` rows with delivery, event, repository, branch, head commit, status, and timing fields.
- The V2 processor uses the GitHub App `installation_id` to generate an installation access token for commit diff fetching.
- Existing added-line parsing, scanner, masking, and AI analysis services are reused.
- Risky detections are stored in `public.v2_detections` with workspace, repository, scan event, commit, file, masked value, severity, confidence, and recommendation fields.
- Raw secret values are never stored in V2 detection payloads.
- Duplicate webhook deliveries with an existing running or completed scan event are skipped to avoid duplicate detections.
- Per-user Discord alerting is still deferred.
- Existing V1 fallback behavior remains for unknown GitHub App install/repo payloads and non-V2 repositories.

## Phase 7.3 Final Phase 7 Verification

Phase 7 completes the Detection Pipeline Upgrade for monitored GitHub App repositories and leaves the application ready for Phase 8 Dashboard V2.

What Phase 7 added:

- GitHub App webhook routing for push payloads that include installation and repository identifiers.
- Workspace repository lookup by `installation_id` + GitHub `repository.id`.
- Repository monitoring checks before any V2 scan work is queued.
- V2 scan event creation and status tracking.
- GitHub App installation-token commit diff fetching.
- V2 detection storage scoped to workspace, repository, scan event, branch, commit, and file location.
- Duplicate delivery protection for running and completed scan events.

V2 webhook routing behavior:

- `/webhook/github` remains public but signature-protected.
- Non-push events are ignored safely after signature verification.
- GitHub App push payloads are checked for `installation.id` and `repository.id`.
- Unknown installations or repositories fall back to the existing V1 webhook path.
- `monitoring_enabled=false` returns a safe skipped response without queueing V1 or V2 processors.
- `monitoring_enabled=true` creates a V2 scan event and queues V2 background processing.

Scan event lifecycle:

- A monitored V2 push creates `public.scan_events` with `status=running`.
- Successful V2 processing marks the scan event `completed` and sets `completed_at`.
- Failed V2 processing marks the scan event `failed`, sets `error_message`, and sets `completed_at`.
- Running or completed events for the same workspace, repository, and GitHub delivery are treated as duplicates.

V2 detection storage behavior:

- Existing added-line parsing, scanner, masking, AI analysis, and risky-detection rules are reused.
- Stored detections go to `public.v2_detections`.
- Stored fields include workspace, repository, scan event, repo, branch, commit, file, line, secret type, masked value, detection method, entropy, severity, confidence, reasoning, recommendation, and status.
- Severity is normalized to the lowercase values allowed by the V2 schema.

Raw secret safety:

- V2 storage includes `masked_value` only.
- `raw_value`, `raw_secret`, and `secret_value` are not part of the V2 detection allowlist.
- The V2 bulk insert helper strips any accidental `raw_value` field defensively before writing to Supabase.

Idempotency behavior:

- Before creating a scan event, the webhook checks for an existing event with the same workspace, repository, and GitHub delivery ID.
- Existing `running` or `completed` events return a duplicate response.
- Duplicate deliveries do not create new scan events or duplicate V2 detections.

V1 fallback preserved:

- Unknown GitHub App installation/repository payloads continue through the existing V1 push processor.
- V1 detection storage in `public.detections` is unchanged.
- V1 notification flow is unchanged.
- V1 scanner rules are unchanged.

Manual test checklist:

- `GET /health` returns public health status.
- Signed non-push webhook returns an ignored response.
- Unsigned or incorrectly signed webhook returns `401`.
- Synced GitHub App repository with monitoring enabled creates a scan event.
- Secret push creates a masked row in `public.v2_detections`.
- V2 detection rows do not contain raw secret values.
- Repeated GitHub delivery returns duplicate and does not duplicate rows.
- Monitoring disabled returns skipped and queues no scan.
- Unknown installation or repository uses V1 fallback safely.
- Existing V1 detection and notification behavior still works.

Intentionally not implemented:

- Per-user Discord alert routing for V2 detections.
- V2 dashboard pages for scan events and detections.
- V1 detection migration.
- Scanner rule changes.
- Queue/retry infrastructure beyond FastAPI background tasks.

Phase 7 is complete and ready for Phase 8 Dashboard V2.
