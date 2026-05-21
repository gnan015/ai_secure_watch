# V2 Phase 2 Supabase Auth

## Phase 2.1 Supabase Frontend Setup

Supabase frontend setup has been added to the React dashboard as the first small step toward V2 authentication.

What changed:

- Added the Supabase JavaScript client dependency to the dashboard.
- Added `dashboard/src/lib/supabase.js` to create and export a configured Supabase client.
- Documented the required frontend environment variables in `dashboard/.env.example`:
  - `VITE_SUPABASE_URL`
  - `VITE_SUPABASE_ANON_KEY`
- Added a development-only warning when either Supabase frontend variable is missing.

What did not change:

- No login UI was added.
- No signup UI was added.
- No protected routes were added.
- No backend JWT verification was added.
- No GitHub App work was added.
- No repository management was added.
- No per-user Discord alert routing was added.
- No detection table migration was added.
- V1 dashboard behavior remains unchanged because the Supabase client is not used anywhere yet.

## Phase 2.2 Planned Next Step

The next phase should introduce Supabase Auth UI and session handling in the dashboard while keeping the existing V1 dashboard available during the transition.
