# Deployment Guide

Host **shopping-monitor** using **Vercel** (frontend) and **Render** (backend). Supabase remains the database and auth provider.

## Production (V1)

| Component | URL / value |
| --- | --- |
| Frontend | `https://shopping-monitor-nine.vercel.app` |
| Backend | `https://shopping-monitor-api.onrender.com` |
| GitHub repo | `https://github.com/rudy-patel/shopping-monitor` |
| Migrations | `001_core_schema.sql` + `002_scrape_job_advisory_lock.sql` + `003_search_cache.sql` — **applied** |

Secrets live in **Render**, **Vercel**, and **GitHub Actions** only — never committed to the repository.

---

## Architecture

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   Vercel     │──API──│   Render     │──DB───│  Supabase    │
│  (frontend)  │       │  (backend)   │       │  (Postgres)  │
│  React/Vite  │       │  FastAPI     │       │  + Auth      │
└──────────────┘       └──────────────┘       └──────────────┘
       ↑                      ↑
  push to main           push to main
  auto-deploys           auto-deploys
```

Both platforms support zero-downtime deploys: traffic stays on the current release until the new build is healthy. Pushes to `main` auto-deploy both services.

## Prerequisites

- GitHub repository
- Supabase project (migrations already applied on production — see [Supabase](#supabase))
- Vercel and Render accounts (GitHub sign-in)

---

## Supabase

### Migrations — status: applied

Both migrations are applied on the production Supabase project:

| Order | File | Purpose |
| --- | --- | --- |
| 1 | `001_core_schema.sql` | Core tables + RLS |
| 2 | `002_scrape_job_advisory_lock.sql` | Advisory-lock RPCs for scrape-all job |
| 3 | `003_search_cache.sql` | Global 24h search-result cache for `/api/search` |

For **new** environments (staging, fresh project), apply in order using one of:

- Supabase MCP `apply_migration`
- `python scripts/apply_supabase_migration.py <filename>` (requires `SUPABASE_ACCESS_TOKEN` in `backend/.env`)
- Supabase SQL editor (paste migration file contents)

### Auth URL configuration

| Setting | Value |
| --- | --- |
| **Site URL** | `https://shopping-monitor-nine.vercel.app` |
| **Redirect URLs** | `https://shopping-monitor-nine.vercel.app/**`, `http://localhost:3000/**`, `https://*.vercel.app/**` (Vercel preview deploys) |

### Google OAuth (H2)

- **Authorized JavaScript origins:** production Vercel URL + `http://localhost:3000`
- **Authorized redirect URI:** `https://<project-ref>.supabase.co/auth/v1/callback`

The frontend uses `redirectTo: window.location.origin` (`AuthContext.tsx`). Every sign-in origin (production, localhost, Vercel previews) must appear in Supabase **Redirect URLs**.

---

## Frontend — Vercel

1. Import the repo at [vercel.com](https://vercel.com).
2. Configure:

| Setting | Value |
| --- | --- |
| Root directory | `frontend` |
| Framework | Vite |
| Production URL | `https://shopping-monitor-nine.vercel.app` |

3. **Environment variables:**

| Variable | Production value |
| --- | --- |
| `VITE_API_URL` | `https://shopping-monitor-api.onrender.com` (no trailing slash) |
| `VITE_SUPABASE_URL` | From Supabase dashboard |
| `VITE_SUPABASE_ANON_KEY` | Anon/publishable key |

4. Deploy. PRs get unique preview URLs. Preview OAuth works because `https://*.vercel.app/**` is in Supabase redirect URLs.

---

## Backend — Render

1. Create a **Web Service** at [render.com](https://render.com) from the same repo.
2. Configure:

| Setting | Value |
| --- | --- |
| Root directory | `backend` |
| Runtime | Python **3.12** |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Production URL | `https://shopping-monitor-api.onrender.com` |

### Playwright on Render

Playwright is **not** in `requirements.txt` and is **not required** for V1 production. The `bestbuy_ca` scraper uses the Best Buy JSON API via `curl_cffi`. Do not add Playwright install steps to the Render build unless a future retailer task (T5.x) requires it. CI Playwright runs **frontend e2e only** (`.github/workflows/ci.yml`).

### Render free tier

The free tier sleeps after ~15 minutes idle with a ~30s cold start on wake (PRD §13). The first request after sleep may be slow. The scrape worker handles deploy lag after pushes to `main` via deploy-wait polling (see [GitHub Actions worker secrets](#github-actions-worker-secrets)).

### Environment variables — required in production

| Variable | Production guidance |
| --- | --- |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role — never expose to frontend |
| `AUTH_BYPASS_ENABLED` | `false` |
| `WORKER_TOKEN` | Strong secret; must match GitHub Actions |
| `APP_BASE_URL` | `https://shopping-monitor-nine.vercel.app` (required for correct digest deep links; backend falls back to this production URL when unset/localhost and `AUTH_BYPASS_ENABLED=false`) |
| `SCRAPER_MODE` | `live` |
| `CORS_ALLOWED_ORIGINS` | `https://shopping-monitor-nine.vercel.app,http://localhost:3000` (comma-separated; include localhost for local frontend → prod API debugging) |
| `GEMINI_API_KEY` | Required for LLM categorization/discovery; heuristics fallback if unset |

### Optional / defaults OK

| Variable | Default / notes |
| --- | --- |
| `GEMINI_MODEL` | `gemini-2.5-flash` |
| `GEMINI_CATEGORIZE_TIMEOUT_S` | `1.5` |
| `GEMINI_DISCOVER_TIMEOUT_S` | `30.0` |
| `GEMINI_SEARCH_TIMEOUT_S` | `12.0` (grounded search; bump if slow in prod) |
| `LOG_LEVEL` | `INFO` |
| `FX_CACHE_TTL_HOURS` | `24` |
| `FRANKFURTER_BASE_URL` | `https://api.frankfurter.dev` |
| `EXCHANGERATE_API_OPEN_URL` | `https://open.er-api.com/v6/latest` |
| `RESEND_FROM_EMAIL` | `Shopping Monitor <onboarding@resend.dev>` (Resend sandbox sender) |

Source of truth: `backend/core/settings.py`.

### Resend (digest email)

| Variable | Notes |
| --- | --- |
| `RESEND_API_KEY` | Required on Render for production digest sends. Local/CI tests mock Resend; unset key → `NoOpMailService`. |
| `RESEND_FROM_EMAIL` | Default sandbox sender above; swap for verified domain in production when ready. |

Sandbox deliverability: Resend `onboarding@resend.dev` only delivers to the Resend account owner email.

---

## GitHub Actions worker secrets

Add these repository secrets:

| Secret | Value |
| --- | --- |
| `BACKEND_BASE_URL` | `https://shopping-monitor-api.onrender.com` |
| `WORKER_TOKEN` | Same value as Render `WORKER_TOKEN` |

### Scrape workflow

`.github/workflows/scrape.yml`:

- **Trigger:** `workflow_dispatch` and cron `0 8 * * *` UTC (≈ 04:00 America/Toronto; enabled T6.3)
- **Worker:** `backend/workers/scrape_all.py`
- **Deploy-wait (PR #32):** If `/internal/jobs/scrape-all` is missing from `/openapi.json`, polls up to 600s (15s interval) before POST — handles Render auto-deploy lag after push to `main`
- **Verified:** [GitHub Actions run #27509008501](https://github.com/rudy-patel/shopping-monitor/actions/runs/27509008501) (2026-06-14) returned `status: "completed"`

Manual run: GitHub → Actions → **Daily scrape** → **Run workflow**.

**Troubleshooting:**

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Timeout waiting for scrape-all route | Render deploy still in progress or wrong `BACKEND_BASE_URL` | Wait for Render deploy; confirm URL is backend not Vercel |
| HTTP 401 on POST | `WORKER_TOKEN` mismatch | Sync Render + GitHub secret |
| HTTP 503 | `WORKER_TOKEN` unset on Render | Set env var |
| `status: "skipped"` | Advisory lock held | Normal for concurrent runs; retry later |

Prior failures ([run #27507830386](https://github.com/rudy-patel/shopping-monitor/actions/runs/27507830386), [run #27508675358](https://github.com/rudy-patel/shopping-monitor/actions/runs/27508675358)) timed out on deploy-wait before PR #32 landed — expected when the scrape route is not yet registered after a deploy.

### Digest workflow

`.github/workflows/digest.yml`:

- **Trigger:** `workflow_dispatch` and cron `0 14 * * *` UTC (fixed Pacific-morning send per PRD §10.3)
- **Worker:** `backend/workers/send_digests.py`
- **Deploy-wait:** Same 600s OpenAPI poll pattern as scrape worker (waits for `/internal/jobs/send-digests`)

Manual run: GitHub → Actions → **Daily digest** → **Run workflow**.

**Production:** `RESEND_API_KEY` and `APP_BASE_URL=https://shopping-monitor-nine.vercel.app` confirmed on Render. Digest live send with unread notifications verified via manual `workflow_dispatch` (T6.2); zero-unread suppression verified in [run #27513581095](https://github.com/rudy-patel/shopping-monitor/actions/runs/27513581095). Cron enabled T6.3 (2026-06-15).

**Troubleshooting:**

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `users_skipped_no_email` | Auth user has no email | Set email on Supabase Auth user (digest resolves via admin API, not `profiles`) |
| `mail_provider: "noop"` | `RESEND_API_KEY` unset on Render | Set env var and redeploy |
| `users_skipped_noop` > 0 with `mail_provider: "noop"` | Same as above — users had qualifying unread rows but no send attempted | Set `RESEND_API_KEY` on Render |
| Second dispatch sends nothing | Idempotency (`email_sent_at` set) | Expected — only unread unsent rows qualify |
| HTTP 401 on POST | `WORKER_TOKEN` mismatch | Sync Render + GitHub secret |

---

## Production verification checklist

```bash
# Backend reachable
curl -sS https://shopping-monitor-api.onrender.com/health | jq .

# OpenAPI includes worker job routes (confirms deploy complete)
curl -sS https://shopping-monitor-api.onrender.com/openapi.json \
  | jq '.paths | has("/internal/jobs/scrape-all")'
curl -sS https://shopping-monitor-api.onrender.com/openapi.json \
  | jq '.paths | has("/internal/jobs/send-digests")'

# Worker token guard (expect 401)
curl -sS -o /dev/null -w "%{http_code}\n" \
  -X POST https://shopping-monitor-api.onrender.com/internal/jobs/scrape-all

# Frontend loads
curl -sS -o /dev/null -w "%{http_code}\n" https://shopping-monitor-nine.vercel.app
```

**Already verified (2026-06-14):**

- Scrape `workflow_dispatch` — [run #27509008501](https://github.com/rudy-patel/shopping-monitor/actions/runs/27509008501) (`listings_total: 13`, `status: completed`)
- Google OAuth — login UI + OAuth redirect verified; owner manual sign-in confirmed
- Live add/refresh on Render — `bestbuy_ca` + `palmisleskate` via `backend/scripts/smoke_production_t6_2.py --live` (T6.2)
- Digest `workflow_dispatch` suppression — [run #27513581095](https://github.com/rudy-patel/shopping-monitor/actions/runs/27513581095) (`mail_provider: resend`, `users_emailed: 0`)
- Account delete — `backend/scripts/smoke_delete_account.py --live --confirm` (disposable user)
- Direct `/login` deep link — `frontend/vercel.json` SPA rewrite (deploy to pick up)

**Health check caveat:** `GET /health` may report `database.status: disconnected` with PostgREST `PGRST205` while Supabase is actually reachable. The scrape job completing successfully is the stronger integration signal until the health probe is hardened (optional T6.2 follow-up).

---

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs lint and unit tests on every push/PR with `SCRAPER_MODE=fixtures` — no live retailer requests.

Playwright e2e runs in the `playwright-e2e` job when Supabase secrets are configured in GitHub Actions; otherwise the job skips with a warning.

---

## Related roadmap tasks

| Task | Relationship |
| --- | --- |
| T6.2 | ~~Full production smoke~~ — **done** (2026-06-14) |
| T6.3 | ~~Enable scrape/digest cron schedules~~ — **done** (2026-06-15) |
| T6.4 | 7-day reliability check |
