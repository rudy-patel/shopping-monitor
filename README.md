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
make benchmark-retailers  # fixture-mode scraper strategy benchmark (T5.1)
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

Milestones **M0–M3** (planning, foundation, local vertical slice, live Best Buy validation) are **done**. **M4** (MVP product workflows) is **done**: discovery, listing review, notifications (read API + evaluators), display currency, scheduled scrape job (T3.5), digest email (T3.6), settings page (T4.2), and account delete (T4.3). **M5** in progress: T5.1 benchmark harness and T5.2 Shopify retailers (`palmisleskate`, `tikiroomskate`) are **done** (`docs/benchmarks/`). **M6** in progress: **T6.2** production smoke is **done** (live `bestbuy_ca` + `palmisleskate` on Render, digest suppression, disposable account delete). Human setup **H4** (Resend) and **H5** (Render/Vercel/GitHub Actions) and deployment docs (**T6.1**) are **done** — production URLs in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). See [`docs/ROADMAP.md`](docs/ROADMAP.md) §15 for the recommended next tasks (T6.3 cron, T5.3 retailers).

## Documentation

- [Product Requirements (V1)](docs/PRD.md)
- [Development Roadmap](docs/ROADMAP.md) — task-level status, PR links, and what to pick up next
- [Scraper benchmark reports](docs/benchmarks/README.md) — per-retailer strategy snapshots (T5.1)
- [Database conventions & RLS](docs/DATABASE.md)
- [Authentication](docs/AUTHENTICATION.md)
- [Deployment (Vercel + Render + Supabase)](docs/DEPLOYMENT.md)

## License

Private project — all rights reserved unless otherwise noted.
