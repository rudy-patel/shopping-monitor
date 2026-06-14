# Agents

## Cursor Cloud specific instructions

### Overview

**Shopping Monitor** — **Python/FastAPI** backend (port 8000) and **React/Vite/TypeScript** frontend (port 3000). Data lives in a remote **Supabase** instance (no local database). See `README.md` and `docs/PRD.md` for full documentation.

Before feature work, read `MEMORY.md`, `docs/PRD.md`, and this file. The PRD is the source of truth for V1 scope, non-goals, data model, worker boundaries, and the first integrated vertical slice.

### Pull requests (agents)

When opening a PR with `gh pr create`:

- Use a **`## Summary`** section only (1–3 bullets: what changed and why).
- **Do not** add a `## Test plan` section with `- [ ]` checkbox tasks. GitHub tracks those as incomplete PR tasks and they can block merge.
- **Do not** list post-merge manual verification (deploy smoke, dashboard checks, production URLs) as PR checkboxes. Put those in the chat if the user needs them; rely on CI for automated checks.
- Optional: one short plain-text sentence for non-obvious manual follow-up — no task list syntax.

### Environment variables

Two `.env` files are needed (not committed). Backend secrets (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `RESEND_API_KEY`, `WORKER_TOKEN`) should be injected as environment variables in the Cursor Cloud secrets panel when using Cloud Agents.

- `backend/.env` — Supabase credentials + `AUTH_BYPASS_ENABLED=true` for local dev (optional until auth is implemented), plus optional V1 service vars:
  - `GEMINI_API_KEY` — LLM discovery/categorization provider key.
  - `RESEND_API_KEY` — daily digest email provider key.
  - `WORKER_TOKEN` — shared secret required by `/internal/jobs/*` endpoints.
  - `APP_BASE_URL` — deployed frontend origin used in email links.
  - `SCRAPER_MODE=fixtures` — local/CI default; valid values: `fixtures`, `live`, `record`.
  - `SUPABASE_ACCESS_TOKEN` — optional; Supabase dashboard **Account → Access Tokens**. Required for agents to apply SQL migrations when MCP is unavailable. (`SUPABASE_SERVICE_ROLE_KEY` alone cannot run DDL.)
- `frontend/.env` — `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL=http://localhost:8000`.

See `backend/.env.example` and `frontend/.env.example` for placeholders. Production URLs and the full env matrix: `docs/DEPLOYMENT.md`.

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
| Scheduled scrape workflow | `.github/workflows/scrape.yml` (`workflow_dispatch` only; cron deferred T6.3) | Requires GitHub secrets `BACKEND_BASE_URL` + `WORKER_TOKEN` matching Render backend. Prod `workflow_dispatch` verified — `docs/DEPLOYMENT.md`. |
| Daily digest workflow | `.github/workflows/digest.yml` (`workflow_dispatch` only; cron deferred T6.3) | Same secrets as scrape; requires `RESEND_API_KEY` on Render for live sends. Local smoke: `python scripts/smoke_resend_digest.py` (dry-run default). |
| Frontend build | `cd frontend && npm run build` | `tsc && vite build` |
| Retailer benchmark | `make benchmark-retailers` | Fixture-mode harness (T5.1); writes `docs/benchmarks/fixtures-YYYY-MM-DD.json` |
| Record Shopify fixtures | `SCRAPER_MODE=record python scripts/record_shopify_fixtures.py --slug palmisleskate --scenario in_stock --url "<product-url>"` | Live capture only; CI uses `SCRAPER_MODE=fixtures` |
| Record structured retailer fixtures | `SCRAPER_MODE=record python scripts/record_retailer_fixtures.py --slug indigo --scenario in_stock --url "<product-url>"` | T5.3 retailers (`indigo`, `apple_ca`, `abercrombie`); live capture only |
| All unit tests | `make test` | Backend pytest (`-m "not integration"`) + frontend vitest |
| Integration tests | `make test-integration` | Requires Supabase credentials; writes `backend/.env` via `make setup-integration-env` |

CI and local automated tests must run scraper code with `SCRAPER_MODE=fixtures` so no test hits live retailer URLs. Use `live` only for explicit benchmark/drift tasks and `record` only when intentionally capturing fixtures.

**Gemini:** pytest and CI never call the live Gemini API. `backend/test/conftest.py` clears `GEMINI_API_KEY` and mocks `genai.Client` for every test. Manual live verification uses `python scripts/smoke_gemini_categorize.py --live` or `python scripts/smoke_gemini_discover.py --live` only (H3); default smoke script paths are dry-run/no-op.

### Integration tests (Supabase RLS smoke)

Integration tests are excluded from `make test` / CI unit jobs. They require a live Supabase project with `001_core_schema` applied.

**Cursor Cloud / local setup**

1. Add these as **Environment Variable** secrets (not Build secrets) in the Cloud Agents dashboard:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_ACCESS_TOKEN` — enables agents to apply migrations via `scripts/apply_supabase_migration.py` when MCP is unavailable
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

### Applying Supabase migrations (agents)

**Service-role keys are not enough** — PostgREST cannot run `CREATE FUNCTION` / DDL. Use one of:

1. **Supabase MCP in Cursor (local):** Project config is `.cursor/mcp.json` → `scripts/run_supabase_mcp.sh` (stdio server, reads `SUPABASE_ACCESS_TOKEN` from `backend/.env`). **Disable duplicate Supabase entries** in **Settings → Tools & MCP** — if both the Supabase plugin and `.cursor/mcp.json` are enabled, the server often shows **Error**. Keep one: prefer the project `mcp.json` setup below. After adding the token, toggle the server off/on or restart Cursor, then call MCP `apply_migration`.

2. **Management API script (fallback):** Same token in `backend/.env`:
   ```bash
   python scripts/apply_supabase_migration.py 002_scrape_job_advisory_lock.sql
   ```

**Setup once:** Add `SUPABASE_ACCESS_TOKEN=sbp_...` to `backend/.env` from [Supabase Access Tokens](https://supabase.com/dashboard/account/tokens) (not the service-role key).

**Troubleshooting**

| Symptom | Fix |
| --- | --- |
| MCP shows **Error** / red status | Disable duplicate Supabase MCP in Settings (plugin vs project `mcp.json`); ensure `SUPABASE_ACCESS_TOKEN` is in `backend/.env`; restart Cursor |
| MCP `server does not exist: supabase` | Start a **new agent turn** after MCP connects; confirm green status under Tools & MCP |
| `Migration API failed (401/403)` | Regenerate PAT; do not use service-role key |
| `PGRST202` on lock RPC after deploy | Migration not applied — run MCP `apply_migration` or `apply_supabase_migration.py` |

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
