# Project Memory

Chronological timeline of completed work, files changed, and known bugs/solutions. Agents: read this before making changes; reference via @MEMORY.md.

---

## [2026-06-10] Project scaffold

**What:** Initial repo from FastAPI + React/Vite + Supabase template. Agent docs (`AGENTS.md`, `.cursor/rules/`), dev tooling (`Makefile`, `dev-servers.sh`), CI skeleton, minimal health API, minimal frontend shell.

**Files:** Project root config, `backend/`, `frontend/`, `docs/`, `.github/workflows/ci.yml`, `scripts/check_migrations.py`.

## [2026-06-10] V1 PRD drafted

**What:** Foundational product requirements document for the Shopping Monitor V1 prototype. Locks scope to: Google SSO, Canada-only with cosmetic display-currency switcher, URL-paste product add with one-shot agentic cross-retailer discovery (Gemini free tier), daily scheduled scrape via GitHub Actions cron hitting backend internal endpoints, 30-day price trend chip, daily digest email via Resend free tier, per-product configurable notification threshold (default 20%), 5 fixed categories, 16 natively supported Canadian retailers plus a generic JSON-LD/OG fallback for any other URL. Shipping/tax/duties explicitly out of scope. Documents data model, API surface, system design, risks, V2 candidates, and V1 success criteria.

**Files:** `docs/PRD.md` (new), `README.md` (linked PRD).

## [2026-06-11] PRD technical direction revised

**What:** Updated the V1 PRD to keep the existing React/Vite + FastAPI + Supabase direction while refining the scraping plan. Firecrawl/hosted scraping APIs are excluded from V1 core operations to preserve indefinite $0 cost. Added a benchmark-first scraper pipeline comparing structured data extraction, `curl_cffi` + parser, and Playwright; retailer modules now choose default strategy/fallbacks from benchmark results. Gemini discovery now references the current free-tier Flash-family model instead of a pinned deprecated model name.

**Files:** `docs/PRD.md`, `MEMORY.md`.

## [2026-06-13] PRD v1.2: wishlist framing, AI categorization, design polish, revisit nudges, dev-iteration guardrails

**What:** Major revision of the V1 PRD based on user feedback. Reframed §1 and §2 around "one organized home for things you want" and healthy-consumerism nudges, with price tracking as the value-add layer. Promoted AI auto-categorization into V1 (sync Gemini Flash call at add time, heuristic fallback, 1.5s timeout, 5 fixed buckets, optional manual override in Add modal). Added a "Design principles" block to §10.1 committing to shadcn/ui, light-default theme with toggle, Framer Motion transitions, optimistic UI, and Lighthouse ≥ 95 targets. Added §5.10 user stories and §7.10 trigger logic for `revisit_on_sale` / `revisit_stale` prompts with 30-day debounce; revisit evaluation slots into the daily scrape worker before digest send (§7.4 step 7). Added §10.9 development load assumptions (~30×/day manual triggers across parallel agents) with per-provider headroom table, advisory-lock concurrency safety, and a hard V1 requirement for §10.10 retailer fixture/mock mode (`SCRAPER_MODE=fixtures|live|record`) plus a weekly drift-detection workflow. Expanded §8 schemas (`profiles.theme`, `profiles.revisit_prompts_enabled`, `profiles.revisit_on_sale_enabled`, `profiles.revisit_stale_enabled`, `profiles.revisit_stale_days`, `products.category_source`, `products.last_user_interaction_at`), §13 risks, §15 success criteria, and §16 open questions. Renamed `DiscoveryProvider` → `LlmProvider` since the same abstraction now serves discovery and categorization.

**Files:** `docs/PRD.md`, `MEMORY.md`.

## [2026-06-13] PRD v1.3: agent-ready architecture/data clarifications

**What:** Clarified V1 implementation boundaries for AI-agent development. Added a first integrated vertical-slice boundary centered on one established retailer (`bestbuy_ca`) before parallel feature expansion. Split daily scrape and digest jobs: scrape runs once daily at `0 8 * * *` UTC and writes in-app notification rows; digest runs separately at `0 14 * * *` UTC for a fixed Pacific-morning send without timezone/daylight-saving logic. Recommended thin GitHub Actions worker scripts that call FastAPI internal endpoints while business logic lives in importable backend services. Tightened data-model gaps: needs-review candidates are `product_listings` rows, count toward the 5-listing cap, and are excluded from best-price/trend/notification math until accepted; listings store `available_variants` and `scrape_snapshot`; profiles now include `notifications_enabled` and drop per-user digest timezone scheduling for V1. Switched trend/price-drop/revisit sale math to product-level daily minimum across accepted/auto-added/primary listings. Fixed PRD formatting issues, aligned docs/CI on Python 3.12, and added local agent/scraper rules, safe env var placeholders, CI `SCRAPER_MODE=fixtures`, and a Supabase schema checklist in `docs/DATABASE.md`.

**Files:** `docs/PRD.md`, `AGENTS.md`, `.cursor/rules/project-memory.mdc`, `docs/DATABASE.md`, `backend/.env.example`, `.github/workflows/ci.yml`, `README.md`, `MEMORY.md`.

## [2026-06-13] V1 roadmap for parallel agent implementation

**What:** Added an agent-ready development roadmap that translates the PRD into prioritized milestones, dependency-aware tasks, just-in-time human setup checkpoints, Supabase MCP approval boundaries, verification expectations, PR sizing guidance, and parallel-agent lanes. The roadmap keeps the first MVP spine focused on a fixture-backed `bestbuy_ca` vertical slice followed by one controlled live Best Buy Canada validation before broad retailer expansion.

**Files:** `docs/ROADMAP.md`, `README.md`, `.cursor/rules/project-memory.mdc`, `MEMORY.md`.

## [2026-06-13] M0 planning baseline closed

**What:** Closed milestone **M0 — Planning baseline** by tightening the agent-doc surface and adding visible progress tracking to the roadmap. `AGENTS.md` now lists `docs/ROADMAP.md` in the "before feature work" reading list alongside `MEMORY.md`, `docs/PRD.md`, and itself, with a one-liner explaining the roadmap's role (sequencing, parallel lanes, human-setup checkpoints). The roadmap gained a status legend (✅ Complete · 🟢 Ready to start · 🟡 Blocked: <reason>), a **Status** column on the M0–M6 milestone table with M0 struck through and marked complete, and a per-task `**Status:**` line on every task block (T0.1 through T7.3) pre-filled with upstream-task and human-setup blockers so the next agent can immediately see what's pickable. T0.1's old `**Status:** this document.` line was replaced with the new ✅ marker. M0 has no upstream dependencies and no required H1–H5 human prerequisite — H1 is the first human checkpoint and is needed for M1 schema/auth verification.

**Files:** `AGENTS.md`, `docs/ROADMAP.md`, `MEMORY.md`.

## [2026-06-14] T1.1 core schema and RLS

**What:** First Supabase migration. Creates `profiles`, `products`, `product_listings`, `price_history`, `notifications`, and `fx_rates_cache` with RLS enabled per `docs/DATABASE.md` (Pattern A on user-owned tables; Pattern B on `fx_rates_cache`). Adds enum check constraints, FK cascades to `auth.users`, `products`, and `product_listings`, indexes for ownership joins and time windows, and a shared `public.handle_updated_at()` trigger applied to `profiles`, `products`, and `product_listings`. Migration applied to the live Supabase project via the Supabase MCP `apply_migration` tool. Structural unit tests assert table/policy/constraint/index/trigger presence; an integration-marked RLS smoke test verifies user A cannot read user B's products. Advisory-lock helper deferred to T3.5.

**Files:** `backend/db/migrations/001_core_schema.sql`, `backend/test/test_migration_001_core_schema.py`, `backend/test/test_rls_smoke.py`, `docs/DATABASE.md`, `docs/ROADMAP.md`, `MEMORY.md`.

## [2026-06-14] T1.1 review pass

**What:** Post-implementation review: tightened migration unit tests (exact CASCADE count, scrape_status nullability, named updated_at triggers), hardened RLS smoke test (dotenv loading, anon-client sign-in, mutation-denial helper, fx_rates_cache Pattern B check, pre-run user cleanup), removed stale duplicate Status line from roadmap T0.1. No schema changes — live migration unchanged.

**Files:** `backend/test/test_migration_001_core_schema.py`, `backend/test/test_rls_smoke.py`, `docs/ROADMAP.md`, `MEMORY.md`.

## [2026-06-14] T1.1 integration test env setup

**What:** Added `scripts/setup_integration_env.py`, `backend/test/conftest.py`, `.cursor/environment.json`, and `make setup-integration-env` / `make test-integration` wiring so RLS smoke tests load `backend/.env` from Cursor secrets or Supabase Management API (`SUPABASE_ACCESS_TOKEN` + `SUPABASE_PROJECT_REF`). `REQUIRE_INTEGRATION_ENV=1` makes missing credentials fail loudly. Remote RLS verified via MCP SQL (`SET LOCAL ROLE authenticated`); PostgREST pytest path requires injected `SUPABASE_*` env vars (not present in automation-launched cloud VM during this session).

**Files:** `scripts/setup_integration_env.py`, `backend/test/conftest.py`, `backend/test/test_rls_smoke.py`, `Makefile`, `AGENTS.md`, `.cursor/environment.json`, `MEMORY.md`.

## [2026-06-14] T1.3 frontend app shell

**What:** Added Tailwind v3 + shadcn/ui scaffolding (button, skeleton, dropdown-menu, dialog, input, label), TanStack Query, react-router-dom v6, Framer Motion, and Sonner. Stand up route layout with top nav, protected-route wrapper, and V1 route stubs. Added API client wrapper (`lib/api.ts`), Auth/Theme/Currency contexts with localStorage persistence, and dev-auth fallback for local iteration without Supabase.

**Files:** `frontend/package.json`, `frontend/tailwind.config.ts`, `frontend/postcss.config.cjs`, `frontend/components.json`, `frontend/src/` (routes, pages, contexts, layout, ui, lib, test).

**Deferred:** real Google OAuth wiring → T2.1; profile-backed theme/currency persistence → T4.1/T4.2; full Add Product flow → T2.6; notification bell badge → T3.3.

**Review follow-up:** Hide TopNav on `/login`; preserve post-login redirect path via `location.state.from`; remove unused `@radix-ui/react-avatar` dep and dead `isProductionBuild` helper; add auth/api/login tests (26 total).
