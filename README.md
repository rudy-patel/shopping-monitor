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
make update-drift-snapshots  # regen drift baselines from fixtures (T5.5; CI-safe)
# SCRAPER_MODE=live make check-retailer-drift  # manual live scraper health check (not CI)
```

### E2E tests

Playwright covers the full fixture-backed `bestbuy_ca` vertical slice (add → category thinking shimmer → detail → refresh → category/threshold → archive with success toast → restore → delete). Runs on **Desktop Chrome** and **Mobile Chrome** (Pixel 5).

**Prerequisites:** Supabase credentials in `backend/.env` (run `make setup-integration-env`), dev auth user `00000000-0000-0000-0000-000000000001` in Supabase Auth, `AUTH_BYPASS_ENABLED=true`, `SCRAPER_MODE=fixtures`.

```bash
make setup-integration-env   # sync backend/.env from secrets
make test-e2e                # auto-starts backend :8000 + frontend :3000
```

CI runs the same spec in the `playwright-e2e` job when GitHub Actions secrets are configured (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, or `SUPABASE_ACCESS_TOKEN` + `SUPABASE_PROJECT_REF`). Without secrets the job skips with a warning.

See `AGENTS.md` for lint/test commands and environment details.

### Implementation status (2026-06-15)

Milestones **M0–M5** and **M8** are **done**. **M6** in progress: **T6.2** production smoke, **T6.3** cron schedules, **T7.1** UI polish, **T7.4** auto-categorization UX, and **T8.1** search-based product addition (⌘K command palette, `/api/search`, 24h cache, `discovery_seed` plumbing) **done**; **T6.4** reliability and **T7.2–T7.3** quality gates remain. Human setup **H1–H5** and deployment docs (**T6.1**) are **done** — production URLs in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). See [`docs/ROADMAP.md`](docs/ROADMAP.md) §15 for next tasks.

### Adding products

Two complementary paths:

- **Search (⌘K / Ctrl+K)** — type any product name; the app searches Canadian retailers via Gemini Flash + Google Search grounding, ranks supported retailers first, then offers best-effort tracking for unsupported retailers. One click on **Track** creates the product and seeds cross-retailer discovery without re-burning LLM quota. Grounded calls parse prompt JSON locally (Gemini 2.5 cannot mix Search grounding with controlled `response_schema`).
- **Add by URL** — header **Add Product** button still accepts a direct product URL when the user already has one.

Both paths share the same scrape / discovery / categorization pipeline. Search results are cached server-side for 24h (`SEARCH_CACHE_TTL_HOURS`). First grounded search per query may take up to ~30s; `SearchThinking` shows rotating status while Gemini runs.

## Documentation

- [Product Requirements (V1)](docs/PRD.md)
- [Development Roadmap](docs/ROADMAP.md) — task-level status, PR links, and what to pick up next
- [Scraper benchmark reports](docs/benchmarks/README.md) — per-retailer strategy snapshots (T5.1)
- [Database conventions & RLS](docs/DATABASE.md)
- [Authentication](docs/AUTHENTICATION.md)
- [Deployment (Vercel + Render + Supabase)](docs/DEPLOYMENT.md)

## License

Private project — all rights reserved unless otherwise noted.
