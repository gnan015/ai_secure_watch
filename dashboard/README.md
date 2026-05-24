# AI SecureWatch Dashboard

React dashboard for viewing AI SecureWatch detections from the FastAPI backend.

## Setup

Install dependencies:

```cmd
npm install
```

Create a local `.env` file from the example:

```cmd
copy .env.example .env
```

Set the backend URL:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_GITHUB_APP_INSTALL_URL=https://github.com/apps/ai-securewatch-scanner/installations/new
```

Run the dashboard:

```cmd
npm run dev
```

The app will run on the URL shown by Vite, usually:

```text
http://localhost:5173
```

## Features

- Summary cards for total, open, critical, high, medium, and resolved detections.
- Recent detections table.
- Full detections table with severity, status, and repository filters.
- Status updates for `open`, `resolved`, and `dismissed`.
- Charts for severity, secret types, and detection trends.
- Safe display rules: the dashboard only shows `masked_value`, never raw secrets.
- GitHub App setup callback route: `/github/setup`.
- Repository page supports GitHub App install/manage, installation save, repository sync, and monitoring toggles.

## GitHub App Setup URL

Configure the GitHub App setup URL so GitHub returns users to the dashboard with `installation_id`:

```text
Local: http://localhost:5173/github/setup
Production: https://your-frontend-domain.com/github/setup
```

The repositories shown in the dashboard are only the repositories available to that GitHub App installation. If the app is installed on all repositories, all accessible repositories can sync. If it is installed on selected repositories, only selected repositories can sync.

## Vercel Deployment

Deploy the `dashboard` folder to Vercel.

Vercel project settings:

```text
Framework Preset: Vite
Build Command: npm run build
Output Directory: dist
```

Production environment variable:

```text
VITE_API_BASE_URL=https://your-railway-backend-url.railway.app
VITE_GITHUB_APP_INSTALL_URL=https://github.com/apps/ai-securewatch-scanner/installations/new
```

Vite only exposes client-side environment variables that start with `VITE_`, so the dashboard API base URL must be named `VITE_API_BASE_URL`.

Before deploying, confirm the production build works:

```cmd
npm run build
```

After deploying the dashboard, copy the Vercel URL and set it in Railway:

```text
FRONTEND_URL=https://your-vercel-dashboard-url.vercel.app
```

This allows the Railway backend CORS policy to accept requests from the deployed dashboard.
