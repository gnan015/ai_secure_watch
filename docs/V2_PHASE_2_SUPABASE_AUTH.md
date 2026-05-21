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

## Phase 2.2 Auth Context And Session Persistence

The dashboard now has a React auth context for future Supabase Auth screens and protected routes.

What changed:

- Added `dashboard/src/context/AuthContext.jsx`.
- Added `AuthProvider` to read the current Supabase session on app load.
- Added `useAuth()` as the helper hook for future authenticated UI.
- Added auth state change listening through `supabase.auth.onAuthStateChange()`.
- Exposed `loading`, `session`, `user`, and `signOut` from the auth context.
- Wrapped the React app with `AuthProvider` in `dashboard/src/main.jsx`.

What did not change:

- No login page was added.
- No signup page was added.
- No logout button was added.
- No protected route was added.
- No dashboard redirect was added.
- No backend JWT verification was added.
- Visible V1 dashboard behavior remains unchanged.

## Phase 2.3 Login Page

The dashboard now has a basic login page powered by Supabase email/password authentication.

What changed:

- Added `dashboard/src/pages/Login.jsx`.
- Installed React Router and added simple dashboard routes.
- Added `/login` for the login page.
- Added `/dashboard` for the existing dashboard.
- Kept `/` rendering the existing dashboard so V1 behavior remains safe.
- Login submits credentials through `supabase.auth.signInWithPassword()`.
- Successful login redirects to `/dashboard`.
- Wrong credentials show the Supabase error message.

What did not change:

- Signup is not added yet.
- Dashboard protection is not added yet.
- Unauthenticated users are not redirected away from the dashboard yet.
- Backend JWT verification is not added yet.
- Existing dashboard API calls are unchanged.
- V1 dashboard behavior remains safe.

## Phase 2.4 Planned Next Step

The next phase should add signup UI and keep route protection as a later, explicit phase.
