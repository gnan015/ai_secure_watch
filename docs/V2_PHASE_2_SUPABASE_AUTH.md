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

## Phase 2.4 GitHub Login With Supabase

The login page now supports GitHub OAuth through Supabase Auth.

What changed:

- Added a primary "Continue with GitHub" button to `dashboard/src/pages/Login.jsx`.
- GitHub OAuth uses `supabase.auth.signInWithOAuth()`.
- Successful GitHub auth redirects back to `/dashboard`.
- GitHub login is for authentication only in this phase.
- Repository access is not requested in this phase.
- Repository monitoring will come later through GitHub App installation.
- Email/password login remains available as a fallback.

Supabase setup required:

- Open Supabase Project -> Authentication -> Providers -> GitHub.
- Enable the GitHub provider.
- Add the GitHub OAuth Client ID.
- Add the GitHub OAuth Client Secret.
- Copy the redirect URL shown by Supabase.
- Paste that redirect URL into the GitHub OAuth App callback URL.

What did not change:

- Signup is not added yet.
- Dashboard protection is not added yet.
- Backend JWT verification is still not added.
- No GitHub App install link was added.
- No repository access code was added.
- Existing dashboard API calls are unchanged.
- V1 dashboard behavior remains unchanged.

## Phase 2.5 Protected Dashboard Route

The dashboard route now requires a Supabase session.

What changed:

- Added `dashboard/src/components/ProtectedRoute.jsx`.
- `/dashboard` now renders the existing dashboard through `ProtectedRoute`.
- Unauthenticated users who open `/dashboard` are redirected to `/login`.
- `/login` remains public.
- Logged-in users who open `/login` are redirected to `/dashboard`.
- `/` redirects based on auth state:
  - logged-in users go to `/dashboard`
  - logged-out users go to `/login`

What did not change:

- Backend routes are unchanged.
- GitHub webhook remains public.
- Scanner logic is unchanged.
- No backend JWT verification was added.
- No GitHub App or repository selection logic was added.
- Existing dashboard API calls are unchanged.
- The V1 dashboard component still works after login.

## Phase 2.6 Logout Button

Authenticated dashboard users can now sign out from the dashboard header.

What changed:

- Added a `Sign out` button to the dashboard header.
- Logout uses the existing `AuthContext` `signOut()` function.
- The button shows `Signing out...` while the request is in progress.
- Successful logout redirects the user to `/login`.
- Logout errors are shown in the existing dashboard alert area.
- The dashboard remains protected by `ProtectedRoute`.

What did not change:

- Backend routes are unchanged.
- GitHub webhook route is unchanged.
- Scanner logic is unchanged.
- No backend JWT verification was added.
- No GitHub App logic was added.
- No repository selection logic was added.
- No per-user Discord alert routing was added.
- Existing dashboard API calls are unchanged.

## Phase 2.7 Profiles Table And RLS

The V2 Supabase profiles table schema has been added as a manual SQL setup file.

What changed:

- Added `backend/supabase_v2_auth_schema.sql`.
- Added a `public.profiles` table linked to `auth.users`.
- Added an `updated_at` trigger for profile updates.
- Added a `handle_new_user()` trigger so new Supabase Auth users automatically get a profile row.
- Added an idempotent backfill query for Supabase Auth users that existed before the profile trigger was installed.
- Profile display names use a safe fallback order:
  - `raw_user_meta_data.name`
  - `raw_user_meta_data.user_name`
  - email prefix
- Profile avatar URLs use `raw_user_meta_data.avatar_url` when available.
- Row Level Security is enabled on `public.profiles`.
- Authenticated users can select only their own profile.
- Authenticated users can update only their own profile.

Manual Supabase setup required:

- Open Supabase Project -> SQL Editor.
- Paste the contents of `backend/supabase_v2_auth_schema.sql`.
- Run the SQL manually.
- If you already logged in before running the SQL, run the latest version of the file again so the backfill creates your profile row.

What did not change:

- GitHub App tables are not added yet.
- Repositories table is not added yet.
- Discord webhook table is not added yet.
- Detections table is not migrated yet.
- Backend JWT verification is still not added.
- Backend runtime routes are unchanged.
- GitHub webhook route is unchanged.
- Scanner logic is unchanged.

## Phase 2.8 Planned Next Step

The next phase should verify profile creation from real Supabase Auth users or add account/profile UI. Backend JWT verification remains a later explicit phase.
