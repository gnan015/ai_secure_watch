# AI SecureWatch Deployment Checklist

Use this checklist before and after deploying AI SecureWatch.

## Backend: Railway

- [ ] Railway deployment is successful.
- [ ] Backend root directory is set to `backend` if deploying from the monorepo.
- [ ] Start command is `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- [ ] `/health` endpoint works after deployment.
- [ ] `APP_ENV=production` is set.
- [ ] `FRONTEND_URL` points to the Vercel dashboard URL.
- [ ] `GITHUB_WEBHOOK_SECRET` is added.
- [ ] `GITHUB_TOKEN` is added.
- [ ] `GEMINI_API_KEY` is added.
- [ ] `SUPABASE_URL` is added.
- [ ] `SUPABASE_SERVICE_ROLE_KEY` is added.
- [ ] `N8N_WEBHOOK_URL` is added.
- [ ] CORS allows the Vercel frontend.
- [ ] GitHub webhook URL is updated to the Railway backend.
- [ ] GitHub webhook secret matches the Railway environment variable.

## Supabase

- [ ] `supabase_schema.sql` has been run in Supabase SQL Editor.
- [ ] `detections` table exists.
- [ ] Data is being inserted after risky detections.
- [ ] Table stores `masked_value`.
- [ ] Table does not store `raw_value`.

## n8n and Discord

- [ ] Production n8n webhook URL is used.
- [ ] Railway `N8N_WEBHOOK_URL` points to the production n8n webhook.
- [ ] n8n workflow is active.
- [ ] Discord alert is received.
- [ ] Discord alert shows only masked secret values.
- [ ] No raw secret appears in Discord.

## Dashboard: Vercel

- [ ] Vercel deployment is successful.
- [ ] Framework preset is `Vite`.
- [ ] Build command is `npm run build`.
- [ ] Output directory is `dist`.
- [ ] `VITE_API_BASE_URL` points to the Railway backend URL.
- [ ] Dashboard loads detections from the backend.
- [ ] Summary cards work.
- [ ] Severity chart works.
- [ ] Secret types chart works.
- [ ] Trend chart works.
- [ ] Full detections table works.
- [ ] Status update action works.
- [ ] Dashboard shows `masked_value` only.
- [ ] Dashboard does not show `raw_value`.

## End-to-End Test

- [ ] Push a fake test secret to the GitHub test repository.
- [ ] FastAPI receives the GitHub webhook.
- [ ] GitHub signature verification succeeds.
- [ ] Commit diff is fetched.
- [ ] Detection is created from added lines.
- [ ] Gemini analyzes the detection.
- [ ] Supabase stores the detection.
- [ ] n8n sends the Discord alert.
- [ ] React dashboard shows the detection.
- [ ] No raw secret is stored, logged, sent, or displayed.

## Security Reminder

- [ ] Never commit real `.env` files.
- [ ] Commit only `.env.example` files.
- [ ] Rotate any real secret that is accidentally pushed during testing.
