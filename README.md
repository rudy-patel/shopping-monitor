# Shopping Monitor

Full-stack app scaffold: **React + Vite** frontend, **FastAPI** backend, **Supabase** for auth and data.

## Quick start

```bash
cd shopping-monitor

make setup    # backend venv + pip + frontend npm install
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
make start    # backend :8000 + frontend :3000
```

Open **http://localhost:3000**.

## Prerequisites

- **Python 3.12** recommended
- **Node.js 20+** (see `.nvmrc`)
- **Supabase** project (optional until you need persistence/auth)

## Project layout

| Path | Purpose |
|------|---------|
| `backend/` | FastAPI API (`uvicorn main:app`) |
| `frontend/` | React/Vite UI |
| `docs/` | PRD, roadmap, auth, database, and deployment guides |
| `AGENTS.md` | Instructions for AI agents / Cursor Cloud |
| `MEMORY.md` | Chronological project history for agents |
| `.cursor/rules/` | Cursor project rules |

## Development commands

```bash
make help           # all targets
make test           # unit tests (backend + frontend)
make test-integration  # pytest -m integration (requires Supabase)
make test-e2e       # Playwright vertical slice (auto-starts servers)
```

### E2E tests

Playwright covers the full fixture-backed `bestbuy_ca` vertical slice (add → detail → refresh → category/threshold → archive → restore → delete).

**Prerequisites:** Supabase credentials in `backend/.env` (run `make setup-integration-env`), dev auth user `00000000-0000-0000-0000-000000000001` in Supabase Auth, `AUTH_BYPASS_ENABLED=true`, `SCRAPER_MODE=fixtures`.

```bash
make setup-integration-env   # sync backend/.env from secrets
make test-e2e                # auto-starts backend :8000 + frontend :3000
```

CI runs the same spec in the `playwright-e2e` job when GitHub Actions secrets are configured (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, or `SUPABASE_ACCESS_TOKEN` + `SUPABASE_PROJECT_REF`). Without secrets the job skips with a warning.

See `AGENTS.md` for lint/test commands and environment details.

### Implementation status (2026-06-14)

Milestones **M0–M3** (planning, foundation, local vertical slice, live Best Buy validation) are **done**. **M4** (MVP product workflows) is **in progress**: discovery, listing review, notifications (read API + evaluators), display currency, and the scheduled scrape job (T3.5) are shipped; **remaining** — digest email (T3.6), settings page (T4.2), account delete (T4.3). Human setup **H5** (Render/Vercel/GitHub Actions) and deployment docs (**T6.1**) are **done** — production URLs in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md); **H4** (Resend) is still **pending**. See [`docs/ROADMAP.md`](docs/ROADMAP.md) §15 for the recommended next tasks.

## Documentation

- [Product Requirements (V1)](docs/PRD.md)
- [Development Roadmap](docs/ROADMAP.md) — task-level status, PR links, and what to pick up next
- [Database conventions & RLS](docs/DATABASE.md)
- [Authentication](docs/AUTHENTICATION.md)
- [Deployment (Vercel + Render + Supabase)](docs/DEPLOYMENT.md)

## License

Private project — all rights reserved unless otherwise noted.
