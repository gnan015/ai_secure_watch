# AI SecureWatch Backend

FastAPI backend setup for AI SecureWatch, a real-time GitHub credential leak detection system.

This project currently includes the basic FastAPI structure, configuration loading, CORS setup, health check endpoints, and a GitHub webhook receiver.

## Project Structure

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── detections.py
│   │   ├── health.py
│   │   └── webhook.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service.py
│   │   ├── database_service.py
│   │   ├── github_service.py
│   │   ├── n8n_service.py
│   │   ├── scanner_service.py
│   │   └── webhook_processor.py
│   └── utils/
│       ├── __init__.py
│       ├── entropy.py
│       ├── github_payload.py
│       ├── masking.py
│       └── signature.py
├── .env.example
├── requirements.txt
├── supabase_schema.sql
└── README.md
```

## Setup

From the `backend` folder, create a virtual environment:

```bash
python -m venv venv
```

Activate the virtual environment on Windows Command Prompt:

```cmd
venv\Scripts\activate
```

Install dependencies:

```cmd
python -m pip install -r requirements.txt
```

Optional: create a local `.env` file from the example file and fill in values later as needed.

```cmd
copy .env.example .env
```

Set your GitHub webhook secret in `.env`:

```text
GITHUB_WEBHOOK_SECRET=your_github_webhook_secret_here
GITHUB_TOKEN=your_github_personal_access_token_here
```

Use the same secret value when creating the webhook in your GitHub repository settings.

`GITHUB_TOKEN` is used by the background processor to call the GitHub REST API and fetch commit details.

## Run the Backend

```cmd
uvicorn app.main:app --reload
```

The API will run at:

```text
http://127.0.0.1:8000
```

## Available Endpoints

### GET /

Returns:

```json
{
  "message": "AI SecureWatch backend is running"
}
```

### GET /health

Returns:

```json
{
  "status": "ok",
  "service": "AI SecureWatch API"
}
```

### POST /webhook/github

Used to receive GitHub push webhook events.

This endpoint verifies the GitHub webhook signature before processing the request. GitHub sends this signature in the `X-Hub-Signature-256` header.

For now, this endpoint reads the GitHub webhook headers and JSON payload, extracts useful push event details, queues background processing, and immediately returns a small summary response. This parsed data will be useful later for commit diff fetching and secret scanning.

GitHub push events are queued with FastAPI background tasks so GitHub gets a fast webhook response. The background processor currently logs the push details only; later it can fetch diffs, scan code, call Gemini, store results, and send alerts.

The background processor now fetches commit details from GitHub for each commit SHA and extracts only newly added lines from each file patch. Removed lines and diff metadata are ignored.

## Regex Secret Scanning

After newly added lines are extracted, the backend scans them with basic regex patterns for common credential leaks such as GitHub tokens, API key assignments, password assignments, database URLs, JWT tokens, private key headers, AWS access keys, and Bearer tokens.

When a potential secret is found, the scanner records the secret type, confidence hint, and detection method. Logs only print masked secret values, never raw secret values.

## Entropy-Based Detection

The backend also checks added lines for suspicious high-entropy strings. Entropy measures how random or unpredictable a string looks. This helps catch custom API keys, tokens, and passwords that do not match a known regex pattern.

Entropy scanning looks at quoted values and config-style assignments, then only checks candidates that are at least 16 characters long, contain both letters and numbers, and are not URLs or normal sentences.

Entropy by itself is not proof that a value is a real secret. It is a useful signal, and a later Gemini AI phase can review detections with more context. Logs still only print masked values.

## Gemini AI Analysis

After regex and entropy scanning find a possible secret, Gemini AI analyzes the masked detection context to reduce false positives. The backend sends the file path, line context with the secret masked, secret type, detection method, confidence hint, and entropy score when available.

Gemini returns structured risk information:

```json
{
  "is_risky": true,
  "risk_level": "HIGH",
  "confidence_score": 0.91,
  "reason": "The value appears to be assigned to an API key variable in application configuration.",
  "recommendation": "Rotate the key immediately and remove it from Git history."
}
```

Allowed risk levels are `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, and `IGNORE`.

If Gemini fails or `GEMINI_API_KEY` is missing, the backend does not crash. It returns a medium-risk fallback so the detection can still be reviewed manually. Raw secret values are not printed in logs.

On Windows ARM64, the backend can use the Gemini REST fallback if the `google-genai` package is skipped during installation.

## Supabase Database Setup

Risky detections can now be stored in Supabase PostgreSQL. The backend stores detection records for later dashboard views, but it only stores `masked_value`. Raw secret values must never be stored in the database.

To set up Supabase:

1. Create a Supabase project.
2. Open the Supabase SQL Editor.
3. Run the SQL in `supabase_schema.sql`.
4. Add these values to `backend/.env`:

```text
SUPABASE_URL=your_supabase_project_url_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
```

5. Install backend dependencies:

```cmd
python -m pip install -r requirements.txt
```

6. Run the backend:

```cmd
uvicorn app.main:app --reload
```

The `SUPABASE_SERVICE_ROLE_KEY` should only be used by the backend. Do not expose it in frontend code. Future dashboard phases can read these detection records without ever needing raw secrets.

On Windows ARM64, the backend can use the Supabase REST fallback if the `supabase` package is skipped during installation.

## n8n Webhook Setup

After a risky detection is stored in Supabase, FastAPI can send the stored masked detection details to an n8n webhook. n8n can later handle automation and alerting. Raw secret values are never sent to n8n.

To set up n8n:

1. Create an n8n workflow.
2. Add a Webhook Trigger node.
3. Copy the production webhook URL.
4. Add it to `backend/.env`:

```text
N8N_WEBHOOK_URL=your_n8n_webhook_url_here
```

5. Install backend dependencies:

```cmd
python -m pip install -r requirements.txt
```

6. Run the backend:

```cmd
uvicorn app.main:app --reload
```

When a risky secret is detected, the backend stores it in Supabase first. If storage succeeds, it sends safe fields such as file path, secret type, masked value, severity, confidence score, AI reasoning, and recommendation to n8n.

## Dashboard API Routes

The backend now exposes safe JSON APIs that a future React dashboard can use to read detections and statistics from Supabase. These routes never return raw secret values.

Available routes:

```text
GET /api/detections
GET /api/detections/recent
GET /api/stats/summary
GET /api/stats/severity
GET /api/stats/secret-types
GET /api/stats/trends
PATCH /api/detections/{id}/status
```

`GET /api/detections` supports optional filters:

```text
status=open
severity=HIGH
repo=username/repo
limit=20
```

Example:

```text
GET /api/detections?severity=HIGH&status=open&limit=20
```

`PATCH /api/detections/{id}/status` accepts:

```json
{
  "status": "resolved"
}
```

Allowed statuses are `open`, `resolved`, and `dismissed`.

Example log output:

```text
Potential secret detected
File: config.py
Secret Type: github_token
Masked Value: ghp_************************3456
Detection Method: regex

AI Analysis:
Risk Level: HIGH
Confidence: 0.91
Reason: The value appears to be assigned to an API key variable in application configuration.
Recommendation: Rotate the key immediately and remove it from Git history.
```

Example entropy log output:

```text
Potential secret detected
File: config.py
Secret Type: high_entropy_string
Masked Value: x7k9************************S0aZ
Detection Method: entropy
Entropy Score: 4.7
```

Example response for a push event:

```json
{
  "status": "queued",
  "event": "push",
  "message": "GitHub push event queued for background processing",
  "data": {
    "repo_full_name": "owner/repository",
    "branch": "main",
    "head_commit_sha": "commit-sha",
    "commit_count": 1
  }
}
```
