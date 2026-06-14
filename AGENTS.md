# Agents

## Cursor Cloud specific instructions

### Overview

**Shopping Monitor** — **Python/FastAPI** backend (port 8000) and **React/Vite/TypeScript** frontend (port 3000). Data lives in a remote **Supabase** instance (no local database). See `README.md` and `docs/PRD.md` for full documentation.

Before feature work, read `MEMORY.md`, `docs/PRD.md`, and this file. The PRD is the source of truth for V1 scope, non-goals, data model, worker boundaries, and the first integrated vertical slice.

### Environment variables

Two `.env` files are needed (not committed). Backend secrets (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `RESEND_API_KEY`, `WORKER_TOKEN`) should be injected as environment variables in the Cursor Cloud secrets panel when using Cloud Agents.

- `backend/.env` — Supabase credentials + `AUTH_BYPASS_ENABLED=true` for local dev (optional until auth is implemented), plus optional V1 service vars:
  - `GEMINI_API_KEY` — LLM discovery/categorization provider key.
  - `RESEND_API_KEY` — daily digest email provider key.
  - `WORKER_TOKEN` — shared secret required by `/internal/jobs/*` endpoints.
  - `APP_BASE_URL` — deployed frontend origin used in email links.
  - `SCRAPER_MODE=fixtures` — local/CI default; valid values: `fixtures`, `live`, `record`.
- `frontend/.env` — `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL=http://localhost:8000`.

See `backend/.env.example` and `frontend/.env.example` for placeholders.

### Running services

```bash
# Backend (in one terminal):
cd backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (in another terminal):
cd frontend && npm run dev
```

Or use `make start` (runs `./dev-servers.sh start` which starts both and blocks).

### Lint / Test / Build

| Check | Command | Notes |
|-------|---------|-------|
| Backend lint | `cd backend && source venv/bin/activate && ruff check .` | CI enforces syntax/critical rules **and** unused imports (`E9,F63,F7,F82,F401`). |
| Frontend lint | `cd frontend && npm run lint` | Zero-warning enforced (`--max-warnings 0`). Unused locals/imports enforced for `src/**` app code; `src/test/**` and `*.test.*` excluded (see `frontend/.eslintrc.cjs`). |
| Backend unit tests | `cd backend && source venv/bin/activate && python -m pytest test/ -v --tb=short -m "not integration"` | Excludes `@pytest.mark.integration`; `make test-backend` uses the same filter. |
| Frontend unit tests | `cd frontend && npm run test:run` | Vitest (`frontend/src/test/`). |
| Frontend live API integration | `cd frontend && VITE_INTEGRATION=1 npm run test:run -- src/test/integration/` | Requires backend on :8000 with `AUTH_BYPASS_ENABLED=true`, `SCRAPER_MODE=fixtures`, Supabase creds. Skipped in default CI. |
| Playwright e2e | `make test-e2e` or `cd frontend && npm run test:e2e` | Auto-starts backend :8000 + frontend :3000 via Playwright `webServer`. Requires Supabase creds in `backend/.env` (`make setup-integration-env`). CI: `playwright-e2e` job runs when GitHub Actions Supabase secrets are set; otherwise skips with a warning. |
| Frontend build | `cd frontend && npm run build` | `tsc && vite build` |
| All unit tests | `make test` | Backend pytest (`-m "not integration"`) + frontend vitest |
| Integration tests | `make test-integration` | Requires Supabase credentials; writes `backend/.env` via `make setup-integration-env` |

CI and local automated tests must run scraper code with `SCRAPER_MODE=fixtures` so no test hits live retailer URLs. Use `live` only for explicit benchmark/drift tasks and `record` only when intentionally capturing fixtures.

**Gemini:** pytest and CI never call the live Gemini API. `backend/test/conftest.py` clears `GEMINI_API_KEY` and mocks `genai.Client` for every test. Manual live verification uses `python scripts/smoke_gemini_categorize.py --live` only (H3); the default smoke script path is dry-run/heuristic.

### Integration tests (Supabase RLS smoke)

Integration tests are excluded from `make test` / CI unit jobs. They require a live Supabase project with `001_core_schema` applied.

**Cursor Cloud / local setup**

1. Add these as **Environment Variable** secrets (not Build secrets) in the Cloud Agents dashboard:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
2. Alternative: set `SUPABASE_ACCESS_TOKEN` (or `SUPABASE_PAT`) + `SUPABASE_PROJECT_REF`; the setup script fetches keys via the Supabase Management API.
3. Sync env and run:
   ```bash
   make setup-integration-env
   make test-integration
   ```
   `make test-integration` sets `REQUIRE_INTEGRATION_ENV=1`, so missing credentials fail loudly instead of skipping.

`scripts/setup_integration_env.py` writes `backend/.env` (gitignored) from shell env, an existing `.env`, or the Management API fallback. It **rejects** `.env.example` placeholder values (`your-project-id`, `your-anon-or-publishable-key`, etc.) — copying the example file alone is not enough.

**Integration test troubleshooting**

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ConnectError` / DNS failure on `your-project-id.supabase.co` | `backend/.env` still has example placeholders | Replace with real project URL + keys from Supabase **Project Settings → API**, or set `SUPABASE_ACCESS_TOKEN` + `SUPABASE_PROJECT_REF` and run `make setup-integration-env` |
| `Missing or placeholder values for: SUPABASE_*` | Setup script or pytest guard detected placeholders | Same as above — do not commit real keys |
| `FK products_user_id_fkey` on product integration tests | Auth-bypass dev user missing | Create user `00000000-0000-0000-0000-000000000001` in Supabase Auth (dashboard or admin API) |
| Agent/cloud VM has secrets but local `make test-integration` fails | Secrets are in Cursor Cloud panel, not local shell/`backend/.env` | Copy secrets into local `backend/.env` once, or export them in your shell before `make setup-integration-env` |

Quick validation after configuring credentials:

```bash
make setup-integration-env   # should print "Wrote backend/.env..."
make test-integration
```

### Gotchas

- **Python venv is mandatory.** Always `source backend/venv/bin/activate` before running any backend Python command. The venv is at `backend/venv/`.
- **Local backend requires Python 3.12.** A 3.9 venv causes Pydantic import errors on `str | None` annotations. Recreate: `python3.12 -m venv venv`.
- **`python3.12-venv`** system package is required to create the venv on Ubuntu 24.04 (not installed by default).
- **Integration tests** use `@pytest.mark.integration` and are excluded from `make test` / `make test-backend`. Run `make test-integration` or `pytest -m integration` with Supabase env and migrations applied.
- **No local database.** All persistence is via remote Supabase.
- **Auth bypass:** Set `AUTH_BYPASS_ENABLED=true` in `backend/.env` for local development without real Supabase auth (when auth routes exist).
- **Supabase security:** Never expose `SUPABASE_SERVICE_ROLE_KEY` to frontend code. Every new `public` table must enable RLS in the same migration and be documented in `docs/DATABASE.md`.
- **Scrapers:** Retailer modules must call `scrapers.http.scraper_fetch()` instead of importing `httpx`/`curl_cffi`/`requests`. See `backend/scrapers/README.md`.
- **Integration env placeholders:** `backend/.env` copied from `.env.example` is rejected by `make setup-integration-env` and integration pytest guards. Use real Supabase credentials (see Integration test troubleshooting above).
