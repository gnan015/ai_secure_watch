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
- New protected GitHub App setup callback route:
`/github/setup`
- Repositories page UI to list synced repositories from the backend.
- GitHub App install/manage button using `VITE_GITHUB_APP_INSTALL_URL`.
- Installation status UI showing the connected GitHub account login.
- Sync repositories action for the authenticated user's saved GitHub App installation.
- Monitoring toggle UI that updates `monitoring_enabled` per repository.
- Loading state, error state, and empty state handling.
- Lightweight navigation link from dashboard header to repositories page.

### API Usage
- Repository list uses protected backend API:
`GET /api/repositories`
- Installation list uses protected backend API:
`GET /api/github/installations`
- Setup callback saves the installation with:
`POST /api/github/installations`
- Repository sync uses:
`POST /api/github/installations/{installation_id}/sync-repositories`
- Monitoring toggle uses protected backend API:
`PATCH /api/repositories/{repository_id}/monitoring`
- Supabase access token is attached by existing dashboard API interceptor.

### Scope Notes
- The repository list is limited to repositories available to the current workspace's GitHub App installation.
- If the GitHub App is installed on all repositories, all accessible repositories can sync.
- If the GitHub App is installed on selected repositories, only selected repositories can sync.
- Users can update GitHub App access in GitHub and click Sync repositories again.
- No webhook/scanner behavior changed.
- Detection pipeline upgrade comes later.

---

## Phase 5.3 Final Phase 5 Verification

Phase 5 Repository Management is complete for backend API and dashboard page scope.

### What Phase 5 Added
- Workspace-scoped backend repository APIs.
- Dashboard repositories page for viewing synced repositories.
- Repository monitoring toggle support.

### Endpoints Added
- `GET /api/repositories`
- `PATCH /api/repositories/{repository_id}/monitoring`

### Dashboard Route Added
- Protected dashboard route:
`/repositories`
- Protected GitHub App setup route:
`/github/setup`

### Manual Test Checklist
- `npm run build` passes in `dashboard`.
- Logged-out access to `/repositories` redirects to `/login`.
- Logged-out access to `/github/setup` redirects to `/login`.
- Logged-in access to `/repositories` loads repository data.
- `/repositories` shows install/manage and sync controls.
- `/github/setup?installation_id=REAL_ID` saves the installation and syncs repositories.
- Synced repositories appear in the repositories table.
- Repeated sync does not create duplicate repository rows.
- Monitoring toggle updates backend and UI state.
- Refresh keeps updated `monitoring_enabled` state.
- `/dashboard` still works as before.
- `/health` remains public.
- `/webhook/github` remains public.

### Intentionally Not Implemented In Phase 5
- Full repository management dashboard flows beyond list + toggle.
- Discord settings and alert routing updates.
- Detection pipeline upgrade work.
- V1 detections migration.
- V1 webhook/scanner behavior changes.

### Readiness
- Phase 5 is complete and ready for **Phase 6 Per-User Discord Alerts**.
