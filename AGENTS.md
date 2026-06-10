# Agents

## Cursor Cloud specific instructions

### Overview

**Shopping Monitor** — **Python/FastAPI** backend (port 8000) and **React/Vite/TypeScript** frontend (port 3000). Data lives in a remote **Supabase** instance (no local database). See `README.md` for full documentation.

### Environment variables

Two `.env` files are needed (not committed). Backend secrets (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`) should be injected as environment variables in the Cursor Cloud secrets panel when using Cloud Agents.

- `backend/.env` — Supabase credentials + `AUTH_BYPASS_ENABLED=true` for local dev (optional until auth is implemented).
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
| Frontend build | `cd frontend && npm run build` | `tsc && vite build` |
| All unit tests | `make test` | Backend pytest (`-m "not integration"`) + frontend vitest |

### Gotchas

- **Python venv is mandatory.** Always `source backend/venv/bin/activate` before running any backend Python command. The venv is at `backend/venv/`.
- **`python3.12-venv`** system package is required to create the venv on Ubuntu 24.04 (not installed by default).
- **Integration tests** use `@pytest.mark.integration` and are excluded from `make test` / `make test-backend`. Run `make test-integration` or `pytest -m integration` with Supabase env and migrations applied.
- **No local database.** All persistence is via remote Supabase.
- **Auth bypass:** Set `AUTH_BYPASS_ENABLED=true` in `backend/.env` for local development without real Supabase auth (when auth routes exist).
