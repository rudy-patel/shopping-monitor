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

Auth routes are not implemented in the scaffold. Wire them when the product needs sign-in.

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
2. Implement a dev-only path that sends requests as a fixed test user UUID (never enable in production).

## OAuth providers

Adding Google/GitHub/etc. on the Supabase dashboard typically requires **no backend changes** if you validate JWTs generically via JWKS and use `auth.uid()` in RLS policies.

## Security notes

- Never expose `SUPABASE_SERVICE_ROLE_KEY` in the frontend.
- Never use `user_metadata` for authorization; use `app_metadata` or your own tables.
- Enable RLS on every `public` table (see `docs/DATABASE.md`).
