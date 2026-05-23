# AI SecureWatch V2 Phase 8: Dashboard V2

## Phase 8.1 Backend V2 Dashboard APIs

Phase 8.1 adds protected backend APIs for reading V2 scan and detection data from the authenticated user's workspace.

- `GET /api/v2/dashboard/overview` returns workspace-scoped repository, scan event, detection, and latest scan summary counts.
- `GET /api/v2/scan-events` returns recent workspace-scoped V2 scan events with optional `status` filtering and bounded `limit`.
- `GET /api/v2/detections` returns workspace-scoped V2 detections with optional `status`, `severity`, `repository_id`, and bounded `limit` filters.
- `PATCH /api/v2/detections/{detection_id}/status` updates status for a workspace-owned V2 detection and sets `resolved_at` when status is `resolved`.
- All Phase 8.1 APIs require Supabase Bearer auth and use backend workspace scoping.
- Detection responses expose `masked_value` only. Raw secret fields are not selected or returned.
- Existing V1 dashboard APIs remain unchanged for backwards compatibility.
- Dashboard UI pages are deferred to Phase 8.2.

## Phase 8.2 Dashboard V2 UI Pages

Phase 8.2 adds authenticated dashboard UI pages for V2 overview, scan events, detections, and detection status workflows.

- V2 overview cards were added to `/dashboard` for repositories, monitored repositories, scan events, failed scans, detections, open detections, critical detections, high detections, and latest scan time.
- `/scan-events` shows recent V2 scan events with loading, error, empty, status filter, repository, branch, commit, status, error, and timestamp states.
- `/detections` shows V2 detections with loading, error, empty, status/severity filters, repository, file location, secret type, `masked_value`, severity, confidence, status, detected time, AI reasoning, and AI recommendation.
- Detection status updates are supported for `open`, `ignored`, `resolved`, and `false_positive`.
- Navigation links were added for Dashboard, Repositories, Discord, Scan Events, and Detections without redesigning the existing layout.
- Raw secrets are never requested or displayed. The UI only renders `masked_value` from the V2 API response.
- V2 APIs remain auth protected and workspace scoped.

## Phase 8.3 Final Phase 8 Verification

Phase 8 completes the Dashboard V2 API and UI implementation needed to view workspace-scoped V2 scan and detection data.

What Phase 8 added:

- Protected backend V2 dashboard APIs.
- V2 overview cards on the authenticated dashboard.
- Authenticated scan events page.
- Authenticated V2 detections page.
- Detection status update controls.
- Navigation links for Dashboard, Repositories, Discord, Scan Events, and Detections.

Backend APIs added:

- `GET /api/v2/dashboard/overview`
- `GET /api/v2/scan-events`
- `GET /api/v2/detections`
- `PATCH /api/v2/detections/{detection_id}/status`

Dashboard routes added:

- `/dashboard` shows V2 overview cards while preserving existing dashboard content.
- `/scan-events` lists recent V2 scan events with status filtering.
- `/detections` lists V2 detections and supports status updates.
- Existing `/repositories`, `/integrations/discord`, and `/login` routes remain available.

Manual test checklist:

- Logged-out users are redirected from `/scan-events` and `/detections` to `/login`.
- Logged-in users can open `/dashboard`, `/scan-events`, `/detections`, `/repositories`, and `/integrations/discord`.
- `/dashboard` loads V2 overview cards.
- `/scan-events` shows loading, error, empty, and table states.
- `/detections` shows loading, error, empty, and table states.
- Detection status can be changed to `open`, `ignored`, `resolved`, or `false_positive`.
- V2 detection rows display `masked_value` only.
- Backend V2 dashboard APIs return `401` without auth.
- `/health` remains public.
- `/webhook/github` remains public and signature-protected.
- Existing V1 dashboard APIs and V1 scanner/detection behavior remain unchanged.

Raw secret safety:

- Dashboard UI does not request or render raw secret fields.
- V2 detection API responses select safe fields only.
- `raw_value`, `raw_secret`, and `secret_value` are not displayed by the V2 UI.

Pending manual verification:

- A manual fake-secret push has not yet produced visible rows in `scan_events` or `v2_detections`.
- Live webhook scan data verification remains pending after Render deployment and GitHub webhook redelivery.
- Do not treat live end-to-end V2 detection ingestion as verified until synced repository webhook delivery creates scan event and V2 detection rows in Supabase.

Intentionally not implemented:

- Dashboard redesign.
- V1 detection migration.
- Scanner rule changes.
- Webhook processing changes.
- GitHub App feature expansion.
- Per-user Discord alert routing for V2 detections.

Phase 8 is complete for dashboard/API implementation and ready for Phase 9 Public Readiness, with live webhook data verification tracked as a manual follow-up.
