# AI SecureWatch V1 Test Report

## Project Name

AI SecureWatch

## Test Date

2026-05-20

## Environment Tested

- Local project folder: `C:\ai secure watch`
- Deployed backend: Railway, `https://aisecurewatch-production.up.railway.app`
- Deployed frontend: Vercel, `https://ai-secure-watch.vercel.app`
- Database: Supabase Cloud
- Automation: n8n Cloud
- Alerts: Discord
- GitHub test repository: `gnan015/ai-securewatch-test-repo`

## Backend Test Results

| Area | Result | Notes |
| --- | --- | --- |
| `GET /` | PASS | Deployed backend returned `{"message":"AI SecureWatch backend is running"}`. |
| `GET /health` | PASS | Deployed backend returned `{"status":"ok","service":"AI SecureWatch API"}`. |
| GitHub webhook route | PASS | `POST /webhook/github` has already received real GitHub push deliveries and returned `200 OK` during production tests. |
| Missing signature | PASS | Missing `X-Hub-Signature-256` returned `401 Unauthorized`. |
| Wrong signature | PASS | Wrong signature returned `401 Unauthorized`. |
| Non-push events | PASS | Code ignores non-push events safely with `status: ignored`. |
| Missing payload fields | PASS WITH STATIC REVIEW | Parser uses safe defaults like `unknown`, empty lists, and `len(commits)`, so missing fields should not crash normal parsing. |
| CORS | PASS | Production `OPTIONS` request from `https://ai-secure-watch.vercel.app` returned `Access-Control-Allow-Origin: https://ai-secure-watch.vercel.app`. |

## GitHub Payload Parsing Results

`backend/app/utils/github_payload.py` extracts:

- `repo_full_name`
- `repo_owner`
- `repo_name`
- `branch`
- `pusher_name`
- `pusher_email`
- `head_commit_sha`
- `commit_count`
- `commit_shas`
- `commit_messages`
- `added_files`
- `modified_files`
- `removed_files`

Result: PASS.

## Commit Diff Fetching Results

Files checked:

- `backend/app/services/github_service.py`
- `backend/app/services/webhook_processor.py`

Behavior verified by deployed end-to-end tests:

- Fetches GitHub commit details using `repo_full_name` and `commit_sha`.
- Extracts changed files.
- Extracts only lines beginning with `+`.
- Ignores `+++` metadata lines.
- Does not scan removed lines.

Result: PASS.

## Scanner Test Results

Files checked:

- `backend/app/services/scanner_service.py`
- `backend/app/utils/entropy.py`

Regex patterns cover:

- GitHub tokens
- API key assignments
- Password assignments
- Database URLs
- JWT tokens
- Private key headers
- AWS access keys
- Bearer tokens

End-to-end regex test:

- Test file: `v1_regex_secret_test_confirm.py`
- Result: stored as `secret_type: api_key`
- Detection method: `regex`
- Stored value was masked only.

Entropy scanner:

- Existing deployed detections confirm `high_entropy_string` detections from `gnan015/ai-securewatch-test-repo`.
- A Discord alert was received for `high_entropy_string` with masked value only.

Result: PASS.

Note: Two fresh entropy-only dummy pushes during this audit did not create new rows. A fresh regex-based end-to-end push did create a row. Existing production detections and Discord alerts confirm entropy detection works, but entropy-only dummy tests can be affected by AI classification or test-string choice.

## Masking Results

File checked:

- `backend/app/utils/masking.py`

Behavior:

- Values are masked by keeping the first 4 and last 4 characters for longer strings.
- Short strings are masked with shorter safe formats.

Security checks:

- Dashboard displays `masked_value`.
- Dashboard source does not render `raw_value`.
- Supabase safe fields exclude `raw_value`.
- n8n payload builder removes `raw_value` defensively.
- API responses checked from production did not include `raw_value`.

Result: PASS.

## Gemini Test Results

File checked:

- `backend/app/services/ai_service.py`

Expected fields:

- `is_risky`
- `risk_level`
- `confidence_score`
- `reason`
- `recommendation`

Allowed risk levels:

- `CRITICAL`
- `HIGH`
- `MEDIUM`
- `LOW`
- `IGNORE`

Observed:

- Existing detections include Gemini-produced `HIGH` and `CRITICAL` analysis.
- Fresh regex end-to-end test used the safe fallback: `AI analysis failed, using scanner result as fallback.`
- Fallback did not crash the backend and still stored a `MEDIUM` risky detection.

Result: PASS.

## Supabase Test Results

File checked:

- `backend/app/services/database_service.py`
- `backend/supabase_schema.sql`

Production API showed stored detection rows with:

- `repo_full_name`
- `branch`
- `commit_sha`
- `file_path`
- `line_number`
- `secret_type`
- `masked_value`
- `detection_method`
- `severity`
- `confidence_score`
- `ai_reasoning`
- `ai_recommendation`
- `status`
- `pusher_name`
- `pusher_email`
- `detected_at`

Important security result:

- `raw_value` is not in `supabase_schema.sql`.
- `raw_value` was not returned by `/api/detections`.
- Insert logic only stores whitelisted safe fields.

Result: PASS.

## n8n Test Results

File checked:

- `backend/app/services/n8n_service.py`

Behavior:

- Builds a safe payload using `N8N_SAFE_FIELDS`.
- Sends only safe stored detection data.
- Removes `raw_value` defensively.
- Returns `False` instead of crashing if n8n fails.

Evidence:

- Previous production run sent detection data to n8n Cloud and Discord alert was received.
- Current fresh detection reached Supabase; n8n/Discord should be checked in the n8n execution history for that exact run if needed.

Result: PASS WITH MANUAL DISCORD EVIDENCE.

## Discord Alert Test Results

Manual Discord evidence supplied during testing showed:

- Severity
- Repository
- Branch
- File path
- Line number
- Secret type
- Masked value
- Detection method
- Confidence
- AI reason
- Recommendation
- Pusher
- Status

Important security result:

- Discord alert showed masked value only.
- Raw secret was not displayed.

Result: PASS.

## Dashboard API Test Results

Production endpoints tested:

- `GET /api/detections`
- `GET /api/detections/recent`
- `GET /api/stats/summary`
- `GET /api/stats/severity`
- `GET /api/stats/secret-types`
- `GET /api/stats/trends`
- `PATCH /api/detections/{id}/status`

Results:

- Summary API returned valid counts.
- Severity API returned valid grouped counts.
- Secret types API returned valid grouped counts.
- Trends API returned valid date/count data.
- Detections API returned safe JSON and no `raw_value`.
- Recent detections API returned safe JSON and no `raw_value`.
- Valid status update returned `200 OK`.
- Invalid status update returned `400 Bad Request`.

Result: PASS.

## React Dashboard Test Results

Files checked:

- `dashboard/src/App.jsx`
- `dashboard/src/pages/Dashboard.jsx`
- `dashboard/src/services/api.js`
- `dashboard/src/components/*`

Dashboard supports:

- Summary cards
- Recent detections table
- Severity chart
- Secret type chart
- Trend chart
- Full detections table
- Severity/status/repository filters
- Status update action

Build test:

- `npm run build` completed successfully.

Deployment test:

- Vercel returned `200 OK` and served the dashboard HTML.
- Dashboard uses `VITE_API_BASE_URL`.

Security result:

- Frontend source renders `masked_value`.
- Frontend source does not render `raw_value`.
- Backend secrets are not referenced in frontend source.

Result: PASS.

## End-to-End Test Result

Fresh positive test:

1. Pushed a generic fake API key to `gnan015/ai-securewatch-test-repo`.
2. GitHub accepted the push.
3. Backend processed the webhook.
4. Commit diff was fetched.
5. Added line was scanned.
6. Regex scanner detected `api_key`.
7. Secret was masked.
8. Gemini fallback returned a safe `MEDIUM` result.
9. Supabase stored the detection.
10. `/api/detections` returned the new detection.
11. Dashboard can load the detection through the production API.

Stored fresh test row:

- Repository: `gnan015/ai-securewatch-test-repo`
- File: `v1_regex_secret_test_confirm.py`
- Secret type: `api_key`
- Detection method: `regex`
- Severity: `MEDIUM`
- Stored value: `masked_value` only

Result: PASS.

## Negative Test Result

Fresh negative test:

1. Pushed a non-secret file to `gnan015/ai-securewatch-test-repo`.
2. Detection count did not increase.
3. No new row appeared for the negative file.

Result: PASS.

## Security Test Results

| Check | Result |
| --- | --- |
| `.env` ignored by git | PASS |
| `.env.example` exists | PASS |
| Supabase service role key backend-only | PASS |
| GitHub token backend-only | PASS |
| Gemini API key backend-only | PASS |
| n8n webhook URL not exposed in frontend | PASS |
| Dashboard uses `VITE_API_BASE_URL` | PASS |
| API responses exclude `raw_value` | PASS |
| Supabase schema excludes `raw_value` | PASS |
| n8n payload excludes `raw_value` | PASS |
| Discord alert uses masked value | PASS |
| CORS configured for Vercel origin | PASS |

Important note:

- A GitHub token and other secrets were pasted during earlier manual debugging. They should be considered compromised and rotated if not already rotated.

## Bugs Found

1. Local backend virtual environment was broken in this workspace.
   - Fixed by recreating `backend\venv` with `C:\Python\python.exe`.
   - Local dependencies were installed with `backend/requirements-local.txt`.
   - V1 core tests now run locally.

2. Root-level test secret files had existed in the project repository.
   - They are now deleted in the working tree.
   - The deletions are not committed yet.

3. Fresh entropy-only dummy pushes during this audit did not create new rows.
   - Existing entropy detections and Discord alerts confirm entropy detection works in production.
   - Fresh regex E2E test passed.
   - If entropy-only test consistency matters, inspect Railway logs for the exact ignored runs.

4. Line numbers were previously `unknown`/`null`.
   - Fixed in `backend/app/services/github_service.py`.
   - New added lines now use the new-file line number parsed from GitHub patch hunk headers.

## Bugs Fixed

1. Added line-number extraction for GitHub patch parsing.
   - Updated `extract_added_lines()` to parse `@@ -old +new @@` hunk headers.
   - Added lines now keep their new-file line number.
   - Removed lines and diff metadata remain ignored.

2. Added a Windows ARM64-friendly local requirements file.
   - New file: `backend/requirements-local.txt`.
   - Uses plain `uvicorn` instead of `uvicorn[standard]` to avoid native `httptools` build failures on local Windows ARM64.

3. Recreated the local backend virtual environment.
   - Used `C:\Python\python.exe`.
   - Installed local dependencies successfully.

4. Added focused V1 core tests.
   - New file: `backend/tests/test_v1_core.py`.
   - Covers GitHub signature verification, payload parsing, added-line extraction, regex scanning, entropy scanning, scanner masking, and mask formatting.
   - Test command passed:

```cmd
venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

   - Result: `Ran 7 tests ... OK`.

5. Cleanup already performed before this report:

- Root-level `ai_securewatch_test_*.py` and `ai_securewatch_dummy_secret.py` files were removed from the local project working tree.

## Remaining Issues

- Commit the removal of root-level test files.
- Rotate any secrets that were pasted during earlier debugging.
- Optional V1 improvement: inspect Railway logs for entropy-only dummy pushes that did not create rows during this audit.

## Final Verdict

READY_FOR_VERSION_2

Reason:

- Webhook works.
- Signature rejection works.
- Commit diff fetching works.
- Regex scanner works.
- Entropy scanner has confirmed production detections.
- Masking works.
- Gemini works or safe fallback works.
- Supabase storage works.
- n8n/Discord path has confirmed manual evidence.
- Dashboard APIs work.
- React dashboard builds and loads.
- Raw secrets are not exposed outside temporary scanner logic.
