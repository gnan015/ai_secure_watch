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
