# V2 Phase 1 Foundation

Phase 1 prepares the V2 direction without implementing the full public platform and without breaking Version 1.

## What Was Reviewed

Backend:

- `backend/app/main.py` creates the FastAPI app, configures CORS, and registers health, webhook, and dashboard API routes.
- `backend/app/routes/webhook.py` receives GitHub push events and verifies webhook signatures.
- `backend/app/services/webhook_processor.py` coordinates commit fetching, added-line extraction, scanning, AI risk review, Supabase storage, and alert forwarding.
- `backend/app/services/scanner_service.py` contains reusable regex and entropy detection logic.
- `backend/app/services/github_service.py` fetches commit details and extracts added lines with file paths and line numbers.
- `backend/app/services/database_service.py` already uses Supabase for safe detection storage and dashboard reads.
- `backend/app/services/n8n_service.py` sends safe alert payloads and removes raw secret values defensively.
- `backend/supabase_schema.sql` defines the current V1 `detections` table.

Dashboard:

- `dashboard/src/App.jsx` currently renders the V1 dashboard directly.
- `dashboard/src/pages/Dashboard.jsx` loads summary, recent detection, table, severity, secret type, and trend data.
- `dashboard/src/services/api.js` centralizes API calls and uses `VITE_API_BASE_URL`.
- Existing dashboard components can be reused for V2 authenticated views.

## Reusable V1 Foundation

- Secret scanners
- Added-line and line-number extraction
- Masking utilities
- GitHub webhook signature verification
- Gemini risk analysis
- Supabase detection storage pattern
- Safe alert payload construction
- Dashboard charts and detection table

## V2 Foundation Prepared

- Added `docs/V2_ROADMAP.md` with public-platform phases.
- Added `docs/V2_ARCHITECTURE.md` with Supabase-based backend, data model, webhook flow, dashboard pages, and security boundaries.
- Added this phase document to record what was prepared.
- Added TODO comments in selected V1 files for later Supabase Auth, GitHub App, and per-user Discord integration.

## Non-Goals For Phase 1

- No full auth implementation.
- No GitHub App implementation.
- No database migration from V1 schema.
- No dashboard routing changes.
- No replacement of the existing webhook or scanner flow.
- No changes that should break the current Render/Vercel deployment.

## Next Phase Recommendation

Start Phase 2 with Supabase Auth:

1. Add Supabase frontend client.
2. Add login and signup pages.
3. Add session handling in React.
4. Add backend JWT verification dependency.
5. Add initial `profiles` table and RLS policy.
6. Keep V1 dashboard available while V2 auth pages are introduced.
