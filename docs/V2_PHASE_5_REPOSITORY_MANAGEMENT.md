# AI SecureWatch V2 Phase 5: Repository Management

## Phase 5.1 Backend Repository APIs

Phase 5.1 adds backend APIs for workspace-scoped repository listing and monitoring toggle.

### Added APIs
- `GET /api/repositories`
  - Lists repositories for the authenticated user's workspace.
  - Returns:
    - `id`
    - `github_repo_id`
    - `full_name`
    - `owner`
    - `name`
    - `private`
    - `default_branch`
    - `html_url`
    - `monitoring_enabled`
    - `created_at`
    - `updated_at`

- `PATCH /api/repositories/{repository_id}/monitoring`
  - Updates `monitoring_enabled` for a repository owned by the authenticated user's workspace.
  - Rejects repository IDs outside the authenticated workspace scope.

### Security And Scope
- Both APIs are protected by Supabase auth (`Authorization: Bearer <token>`).
- Repository access is limited to the authenticated user's workspace.
- Backend uses service-role credentials only on backend-side Supabase calls.

### Deferred
- Dashboard repositories UI is deferred to **Phase 5.2**.

### Compatibility Notes
- V1 webhook endpoint behavior is unchanged.
- V1 scanner logic is unchanged.
- V1 detections behavior is unchanged.

---

## Phase 5.2 Dashboard Repositories Page

Phase 5.2 adds the first repository management page in the dashboard.

### What Was Added
- New protected dashboard route:
`/repositories`
- Repositories page UI to list synced repositories from the backend.
- Monitoring toggle UI that updates `monitoring_enabled` per repository.
- Loading state, error state, and empty state handling.
- Lightweight navigation link from dashboard header to repositories page.

### API Usage
- Repository list uses protected backend API:
`GET /api/repositories`
- Monitoring toggle uses protected backend API:
`PATCH /api/repositories/{repository_id}/monitoring`
- Supabase access token is attached by existing dashboard API interceptor.

### Scope Notes
- No webhook/scanner behavior changed.
- Detection pipeline upgrade comes later.
