# AI SecureWatch

[![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-dashboard-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Supabase](https://img.shields.io/badge/Supabase-auth%20%26%20database-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com/)
[![Security](https://img.shields.io/badge/Security-secret%20scanning-blue)](#features)
[![Status](https://img.shields.io/badge/Status-V2%20MVP%20complete-brightgreen)](docs/V2_ROADMAP.md)

## 3-Line Description

AI SecureWatch is a GitHub credential leak detection platform for finding exposed secrets in newly pushed code.
It verifies GitHub webhooks, scans added lines, masks sensitive values, and enriches detections with AI risk analysis.
The project includes a FastAPI backend, Supabase storage/auth, Discord alerting, and a React dashboard for reviewing findings.

## Problem It Solves

Developers can accidentally push API keys, tokens, private keys, database URLs, and other sensitive values to GitHub. Even short exposure windows can create security incidents.

AI SecureWatch reduces that risk by monitoring GitHub push events, scanning only newly added code, storing safe masked detection records, and alerting teams quickly so credentials can be rotated and removed.

## Features

- GitHub webhook receiver with signature verification.
- GitHub App based V2 flow for installation-scoped repository monitoring.
- Commit diff fetching that scans added lines instead of entire repositories.
- Regex detection for common secrets such as GitHub tokens, API keys, passwords, database URLs, JWTs, AWS keys, private key headers, and bearer tokens.
- Entropy-based detection for suspicious custom tokens.
- Gemini AI analysis for risk level, confidence, reasoning, and remediation guidance.
- Supabase persistence with masked detection values only.
- Supabase Auth powered dashboard sessions.
- Workspace-scoped V2 APIs for repositories, scan events, detections, and dashboard overview data.
- Repository monitoring toggles.
- Encrypted per-workspace Discord webhook management with test alerts.
- V1 fallback path for legacy webhook scanning.
- React dashboard with summary cards, charts, recent detections, filters, status updates, repository management, scan events, GitHub setup, and Discord settings.
- Production readiness docs, deployment checklist, launch hardening notes, and test coverage for safety boundaries.

## Tech Stack

| Area | Tools |
| --- | --- |
| Backend | Python, FastAPI, Uvicorn, Pydantic Settings |
| Frontend | React, Vite, React Router, Axios, Chart.js |
| Auth and database | Supabase Auth, Supabase PostgreSQL, RLS |
| Security scanning | Regex rules, entropy scoring, safe masking |
| AI analysis | Gemini API |
| Integrations | GitHub Webhooks, GitHub App APIs, Discord webhooks, n8n |
| Testing | Pytest, FastAPI TestClient, dashboard production build checks |
| Deployment targets | Railway or Render for backend, Vercel for dashboard, Supabase Cloud |

## Architecture Flow

```text
Developer pushes code to GitHub
        |
        v
GitHub sends push webhook to FastAPI
        |
        v
Backend verifies X-Hub-Signature-256
        |
        v
V2 route maps installation + repository to a workspace
        |
        v
Backend fetches commit diffs with a GitHub App installation token
        |
        v
Scanner extracts added lines and runs regex + entropy checks
        |
        v
Gemini reviews masked detection context and returns risk metadata
        |
        v
Supabase stores workspace-scoped masked detections and scan events
        |
        v
Discord/n8n receive safe alert payloads
        |
        v
React dashboard displays overview, scan events, detections, and actions
```

## Folder Structure

```text
.
|-- backend/
|   |-- app/
|   |   |-- dependencies/        # Auth dependencies and request context
|   |   |-- routes/              # Health, webhook, dashboard, GitHub, repository, Discord APIs
|   |   |-- services/            # GitHub, scanner, AI, database, Discord, and webhook processors
|   |   `-- utils/               # Signature verification, masking, entropy, payload parsing, safe logging
|   |-- tests/                   # V1, V2, launch safety, and API tests
|   |-- requirements.txt
|   |-- supabase_schema.sql
|   |-- supabase_v2_auth_schema.sql
|   |-- supabase_v2_multi_user_schema.sql
|   `-- README.md
|-- dashboard/
|   |-- src/
|   |   |-- components/          # Tables, charts, cards, layout, protected route
|   |   |-- context/             # Auth context
|   |   |-- lib/                 # Supabase client
|   |   |-- pages/               # Dashboard, detections, repositories, Discord, GitHub setup
|   |   `-- services/            # API client
|   |-- package.json
|   |-- vite.config.js
|   `-- README.md
|-- docs/                        # V2 architecture, roadmap, phase notes, launch hardening
|-- docs/screenshots/            # Add project screenshots here
|-- DEPLOYMENT_CHECKLIST.md
|-- TEST_REPORT.md
|-- .env.example
`-- .gitignore
```

## Setup Instructions

### 1. Clone the Repository

```powershell
git clone https://github.com/your-username/ai-securewatch.git
cd ai-securewatch
```

### 2. Configure Backend Environment

```powershell
cd backend
Copy-Item .env.example .env
```

Fill in `backend/.env` with your own GitHub, Supabase, Gemini, and alerting values. Do not commit real secrets.

### 3. Install Backend Dependencies

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 4. Prepare Supabase

Run the SQL files you need in the Supabase SQL Editor:

```text
backend/supabase_schema.sql
backend/supabase_v2_auth_schema.sql
backend/supabase_v2_multi_user_schema.sql
```

Use the V1 schema for the original detection flow and the V2 schemas for auth, workspaces, GitHub installations, repositories, Discord webhooks, scan events, and V2 detections.

### 5. Run the Backend

```powershell
uvicorn app.main:app --reload
```

The backend runs at:

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

### 6. Configure Dashboard Environment

Open a new terminal:

```powershell
cd dashboard
Copy-Item .env.example .env
```

Set the public dashboard values:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_SUPABASE_URL=your_supabase_project_url_here
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key_here
VITE_GITHUB_APP_INSTALL_URL=https://github.com/apps/your-github-app/installations/new
```

### 7. Install and Run the Dashboard

```powershell
npm install
npm run dev
```

The dashboard usually runs at:

```text
http://localhost:5173
```

### 8. Optional Production Build

```powershell
npm run build
```

## Environment Variables

Use `.env.example`, `backend/.env.example`, and `dashboard/.env.example` as safe templates. Keep real values in local `.env` files or hosting provider secrets.

| Variable | Used by | Purpose |
| --- | --- | --- |
| `APP_NAME` | Backend | FastAPI application name |
| `APP_ENV` | Backend | Development or production mode |
| `FRONTEND_URL` | Backend | Allowed dashboard origin for CORS |
| `GITHUB_WEBHOOK_SECRET` | Backend | Verifies GitHub webhook signatures |
| `GITHUB_TOKEN` | Backend | Legacy V1 GitHub commit fetch path |
| `GITHUB_APP_ID` | Backend | GitHub App identifier |
| `GITHUB_APP_PRIVATE_KEY` | Backend | Signs GitHub App JWTs |
| `GITHUB_APP_WEBHOOK_SECRET` | Backend | GitHub App webhook secret placeholder |
| `GITHUB_APP_CLIENT_ID` | Backend | GitHub App client ID |
| `GITHUB_APP_CLIENT_SECRET` | Backend | GitHub App client secret |
| `GEMINI_API_KEY` | Backend | AI risk analysis |
| `SUPABASE_URL` | Backend | Supabase project URL |
| `SUPABASE_ANON_KEY` | Backend and dashboard | Public Supabase client key |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend only | Trusted database writes and reads |
| `SUPABASE_JWT_SECRET` | Backend | Supabase JWT verification |
| `N8N_WEBHOOK_URL` | Backend | Optional automation webhook for alerts |
| `DISCORD_WEBHOOK_ENCRYPTION_KEY` | Backend | Encrypts saved Discord webhook URLs |
| `VITE_API_BASE_URL` | Dashboard | FastAPI base URL |
| `VITE_SUPABASE_URL` | Dashboard | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Dashboard | Public Supabase anon key |
| `VITE_GITHUB_APP_INSTALL_URL` | Dashboard | GitHub App installation URL |

Backend-only secrets must never be placed in the dashboard environment.

## Screenshots

Screenshots should be placed in [`docs/screenshots`](docs/screenshots/). Placeholder notes are already included there so the folder is visible in Git.

Recommended screenshots:

- `dashboard-overview.png` - summary cards, charts, and recent detections.
- `detections-table.png` - filtered detections with masked values and status controls.
- `repositories.png` - synced repositories with monitoring toggles.
- `discord-settings.png` - masked Discord webhook settings and test action.
- `scan-events.png` - recent scan event history.
- `github-setup.png` - GitHub App installation/setup flow.

## Demo Workflow

1. Start the FastAPI backend and React dashboard locally.
2. Sign in through Supabase Auth.
3. Install the GitHub App on a test repository.
4. Save the installation from the dashboard and sync repositories.
5. Enable monitoring for a repository.
6. Add and test a Discord webhook from the dashboard.
7. Push a fake test secret to the monitored repository.
8. Confirm GitHub sends a webhook to `/webhook/github`.
9. Confirm a scan event and masked detection appear in Supabase.
10. Confirm the dashboard updates and the Discord alert contains only masked values.
11. Resolve or dismiss the detection from the dashboard.

## Security Notes

- Raw secrets are masked before storage, alerts, API responses, and dashboard rendering.
- Supabase service role keys, JWT secrets, GitHub App private keys, Discord webhook URLs, and encryption keys are backend-only.
- GitHub webhook signature verification is required before processing push events.
- V2 dashboard APIs are authenticated and scoped to the user's workspace.
- Discord webhook URLs are encrypted at rest and displayed only with safe last-four metadata.

## Documentation

- [Backend README](backend/README.md)
- [Dashboard README](dashboard/README.md)
- [V2 Architecture](docs/V2_ARCHITECTURE.md)
- [V2 Roadmap](docs/V2_ROADMAP.md)
- [Deployment Checklist](DEPLOYMENT_CHECKLIST.md)
- [Test Report](TEST_REPORT.md)
- [Launch Hardening](docs/V2_PHASE_10_LAUNCH_HARDENING.md)

## Future Improvements

- Billing and subscription support.
- Organization and team management UI.
- Stronger onboarding for first-time users.
- Pull request comments for detected secrets.
- Email and Slack alert channels.
- Background worker queue for large webhook workloads.
- Advanced rate limiting and abuse controls.
- More scanner rules and provider-specific secret validation.
- Dashboard visual polish and deeper analytics.
- Supabase backup/export automation before schema changes.
