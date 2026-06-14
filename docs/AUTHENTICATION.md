# Authentication Guide

Auth setup and API usage for **shopping-monitor**.

## Overview

The stack uses **Supabase Auth** with **JWT tokens** validated on the FastAPI backend via JWKS (recommended for Supabase ECC signing keys).

```
┌──────────┐      ┌─────────────┐      ┌─────────────┐      ┌──────────┐
│ Frontend │─────▶│  Supabase   │─────▶│   Backend   │─────▶│ Database │
│  (React) │ JWT  │    Auth     │ JWKS │  (FastAPI)  │ RLS  │(Postgres)│
└──────────┘      └─────────────┘      └─────────────┘      └──────────┘
```

Auth routes use Supabase Google OAuth on the frontend and JWT validation on the backend. Profile settings are bootstrapped via `GET /api/profile`.

## Profile bootstrap

### `GET /api/profile`

Returns the authenticated user's settings row. If no row exists for the user, the backend inserts a row with PRD §8.1 defaults and returns it (idempotent upsert on first access).

Defaults: `display_currency=CAD`, `default_threshold_pct=20`, `notifications_enabled=true`, `email_digest_enabled=true`, `theme=light`, revisit prompt flags enabled, `revisit_stale_days=30`.

Requires a valid bearer token (or auth bypass in local dev).

### `PATCH /api/profile`

Partial update of profile fields. Only supplied fields are changed. Constraints:

| Field | Allowed values |
| --- | --- |
| `display_currency` | `CAD`, `USD`, `EUR`, `GBP` |
| `default_threshold_pct` | 1–95 |
| `theme` | `light`, `dark` |
| `revisit_stale_days` | 7–365 |

Unknown fields are rejected (422). Empty body returns 400.

Implementation: `backend/services/profile_service.py`, `backend/routers/profile.py`. Frontend hooks: `useProfile`, `useUpdateProfile` (called from `ProtectedRoute` to bootstrap on first authenticated render).

## Google OAuth (Supabase)

Human setup (H2):

1. Create a Google Cloud OAuth 2.0 client (Web application).
2. Enable **Google** as a provider in Supabase Auth (Dashboard → Authentication → Providers).
3. Add redirect URLs for your local frontend dev server and your deployed production frontend origin. Supabase handles the OAuth callback; the frontend uses `signInWithOAuth({ provider: 'google', options: { redirectTo: window.location.origin } })` so users land on `/` after sign-in.

## Environment

**Backend (`backend/.env`):**

```bash
SUPABASE_URL=https://<project-id>.supabase.co
SUPABASE_ANON_KEY=sb_publishable_...
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...
AUTH_BYPASS_ENABLED=true   # local dev only
```

**Frontend (`frontend/.env`):**

```bash
VITE_SUPABASE_URL=https://<project-id>.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_...
VITE_API_URL=http://localhost:8000
```

## Local auth bypass (development)

1. Set `AUTH_BYPASS_ENABLED=true` in `backend/.env`.
2. `get_current_user` (in `backend/core/auth.py`) returns a fixed dev user UUID without a bearer token. Never enable in production.

## OAuth providers

Adding Google/GitHub/etc. on the Supabase dashboard typically requires **no backend changes** if you validate JWTs generically via JWKS and use `auth.uid()` in RLS policies.

## Security notes

- Never expose `SUPABASE_SERVICE_ROLE_KEY` in the frontend.
- Never use `user_metadata` for authorization; use `app_metadata` or your own tables.
- Enable RLS on every `public` table (see `docs/DATABASE.md`).

## Implementation modules

| Module | Purpose |
| --- | --- |
| `backend/core/settings.py` | Central settings loader (`pydantic-settings`); env vars for Supabase, auth bypass, worker token, Gemini, Resend, app URL, scraper mode, CORS, log level. |
| `backend/core/auth.py` | `get_current_user` FastAPI dependency; Supabase JWT validation via JWKS (RS256/ES256); auth-bypass dev path. |
| `backend/core/security.py` | `require_worker_token` dependency for `/internal/jobs/*` (fail-closed 503 when `WORKER_TOKEN` unset). |
| `backend/core/logging.py` | Structured JSON logging (`configure_logging`, `get_logger`). |

### Auth bypass (`AUTH_BYPASS_ENABLED=true`)

For **local development only**. When enabled, `get_current_user` returns a fixed dev user without a bearer token:

- **User UUID:** `00000000-0000-0000-0000-000000000001`
- **Email:** `dev@local.test`
- **Role:** `authenticated`

**Never enable in production.** Default is `false`; `backend/.env.example` sets `true` for local dev convenience.
