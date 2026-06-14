# Deployment Guide

Host **shopping-monitor** using **Vercel** (frontend) and **Render** (backend). Supabase remains the database and auth provider.

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

Both platforms support zero-downtime deploys: traffic stays on the current release until the new build is healthy.

## Prerequisites

- GitHub repository
- Supabase project
- Vercel and Render accounts (GitHub sign-in)

---

## 1. Frontend (Vercel)

1. Import the repo at [vercel.com](https://vercel.com).
2. **Root Directory:** `frontend`
3. **Framework:** Vite
4. **Environment variables:**

   | Variable | Value |
   |----------|-------|
   | `VITE_API_URL` | Your Render backend URL (no trailing slash) |
   | `VITE_SUPABASE_URL` | From Supabase dashboard |
   | `VITE_SUPABASE_ANON_KEY` | Publishable/anon key from Supabase |

5. Deploy. Pushes to `main` auto-deploy; PRs get preview URLs.

---

## 2. Backend (Render)

1. Create a **Web Service** at [render.com](https://render.com) from the same repo.
2. **Root Directory:** `backend`
3. **Build command:** `pip install -r requirements.txt`
4. **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. **Environment variables:**

   | Variable | Value |
   |----------|-------|
   | `SUPABASE_URL` | From Supabase |
   | `SUPABASE_ANON_KEY` | Anon/publishable key |
   | `SUPABASE_SERVICE_ROLE_KEY` | Secret key (never expose to frontend) |
   | `AUTH_BYPASS_ENABLED` | `false` in production |
   | `WORKER_TOKEN` | Shared secret for `POST /internal/jobs/*` (must match GitHub Actions) |
   | `APP_BASE_URL` | Deployed frontend origin (email links; T3.6 digest) |
   | `SCRAPER_MODE` | `live` in production; `fixtures` for local/CI |
   | `GEMINI_API_KEY` | LLM categorization/discovery (optional until those paths run) |
   | `RESEND_API_KEY` | Digest email provider (T3.6; optional until digest job) |

6. Use the service URL for `VITE_API_URL` on Vercel.

### GitHub Actions worker secrets

Scheduled jobs call the deployed backend over HTTP. Add these repository secrets:

| Secret | Value |
|--------|-------|
| `BACKEND_BASE_URL` | Render backend URL (no trailing slash) |
| `WORKER_TOKEN` | Same value as Render `WORKER_TOKEN` |

**Scrape job (T3.5):** `.github/workflows/scrape.yml` supports manual `workflow_dispatch` only. Do not enable the cron schedule until T6.3 production validation is complete.

1. GitHub → Actions → **Daily scrape** → **Run workflow**
2. Confirm Render logs show `scrape_all_completed` JSON and response `status: completed` (or `skipped` if a concurrent run holds the advisory lock)

---

## 3. Supabase

1. Apply migrations from `backend/db/migrations/` via Supabase SQL editor or CLI.
2. Configure Auth providers and redirect URLs for your Vercel domain.
3. Store secrets in Render/Vercel/GitHub Actions — not in the repo.

---

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs lint and unit tests on every push/PR. Integration tests can be added when Supabase secrets are configured in a GitHub **Environment**.
