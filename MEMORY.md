# Project Memory

Chronological timeline of completed work, files changed, and known bugs/solutions. Agents: read this before making changes; reference via @MEMORY.md.

---

## [2026-06-14] conftest integration setup gating fix

**What:** Fixed noisy `pytest_configure` hook in `backend/test/conftest.py`: substring check on `markexpr` treated `-m "not integration"` as a positive integration selection and ran `scripts/setup_integration_env.py` on every unit test invocation. Replaced with pytest's `Expression` evaluator so negated filters are handled correctly. Added subprocess regression test proving unit-test collection does not emit Supabase setup warnings.

**Files:** `backend/test/conftest.py`, `backend/test/test_conftest_integration_hook.py`, `MEMORY.md`.

## [2026-06-14] T1.5 review pass

**What:** Second-pass cleanup: fixed categorizer import order, replaced `type: ignore` with `cast`, guarded invalid retailer-default slugs in `heuristic_category`, added tz-aware validation on `NotificationEvaluationContext.evaluated_at`, parametrized LLM-fallback categorizer tests, and added coverage for `StaticFxService.get_rates`, invalid digest `to_email`, public `services` re-exports, orchestrator retailer-default path, and invalid retailer-default rejection.

**Files:** `backend/services/categorizer.py`, `backend/services/notifications.py`, `backend/services/README.md`, `backend/test/test_services_categorizer.py`, `backend/test/test_services_fx.py`, `backend/test/test_services_mail.py`, `backend/test/test_services_notifications.py`, `backend/test/test_services_init.py`, `MEMORY.md`.

## [2026-06-14] T1.5 service interfaces

**What:** Added the `backend/services/` package: `LlmProvider`/`Categorizer`/`FxService`/`MailService`/`NotificationEvaluator` Protocols, per-kind notification evaluator stubs (`PriceDropEvaluator`, `BackInStockEvaluator`, `ScrapeFailingEvaluator`, `RevisitOnSaleEvaluator`, `RevisitStaleEvaluator`) returning `[]`, no-op/fake providers (`NoOpLlmProvider`, `FakeLlmProvider`, `StaticFxService`, `NoOpMailService`, `NullNotificationEvaluator`, `RecordingNotificationEvaluator`, `CompositeNotificationEvaluator`), `DefaultCategorizer` orchestrator with manual→LLM→heuristic→`default_other` waterfall, and a `pricing` module with §7.4/§7.5/§7.10 constants, eligibility filter, daily-minimum, trend (±3% deadband, 7-day floor), price-drop, and revisit-on-sale helpers. All providers are pure in-memory; no new runtime deps. Unit tests cover heuristic categorizer fallbacks across all `LlmProviderError` subclasses, trend boundary cases (incl. ±3% inclusive), eligibility filter (`needs_review`/`rejected`/out-of-stock excluded), FX identity/conversion/unknown-quote, composite evaluator concatenation, and exact `NotificationKind` parity with the migration check constraint.

**Files:** `backend/services/__init__.py`, `backend/services/README.md`, `backend/services/llm.py`, `backend/services/categorizer.py`, `backend/services/fx.py`, `backend/services/mail.py`, `backend/services/notifications.py`, `backend/services/pricing.py`, `backend/test/test_services_llm.py`, `backend/test/test_services_categorizer.py`, `backend/test/test_services_fx.py`, `backend/test/test_services_mail.py`, `backend/test/test_services_notifications.py`, `backend/test/test_services_pricing.py`, `docs/ROADMAP.md`, `MEMORY.md`.

**Deferred:** Gemini Flash `LlmProvider` impl → T2.4 (categorize) / T3.1 (discover); evaluator bodies for price-drop/back-in-stock/scrape-failing/revisit → T3.4; Resend `MailService` + HTML/text digest templates → T3.6; Frankfurter primary + `exchangerate.host` fallback + 24h `fx_rates_cache` → T4.1; tightening `NotificationEvaluationContext` placeholder `dict[str, Any]` fields into typed snapshots → T3.4; swapping `DigestEmail.to_email: str` for `EmailStr` once `email-validator` is added → T3.6.

## [2026-06-14] T1.4 review pass

**What:** Second-pass code review: proxied `get_scraper_mode()` to `core.settings.get_settings()` (T1.2 integration), fixed `FixtureLoader.iter_scenarios()` to return an empty iterator instead of `None` for missing retailer dirs, scoped scraper autouse conftest hooks to scraper test modules only, aligned mode tests with settings `Literal` validation (canonical lowercase values; non-canonical casing raises `ScraperConfigError`), used the fixture-mode check helper in `http.py`, added tests for the require-fixture-mode guard, registry error context, fixture loader bytes/invalid-ext/missing-dir paths, and cleaned README/exception docstrings.

**Files:** `backend/scrapers/mode.py`, `backend/scrapers/http.py`, `backend/scrapers/fixture_loader module`, `backend/scrapers/exceptions.py`, `backend/scrapers/README.md`, `backend/test/conftest.py`, `backend/test/test_scraper_mode.py`, `backend/test/test_scraper_registry.py`, `backend/test/test_fixture_loader.py`, `MEMORY.md`.

## [2026-06-14] T1.4 scraper contract and fixture harness

**What:** Added the `backend/scrapers/` package: `ProductSnapshot`/`VariantAttribute`/`VariantCombination`/`ScrapeSource` Pydantic contract, `ScraperMode` enum with `get_scraper_mode()` defaulting to fixture mode, a `ScraperError` hierarchy (including `the fixture-mode network guard error`), in-process retailer registry with host-suffix URL lookup, and a `FixtureLoader` covering load/exists/iter plus an explicit atomic `record(...)` writer. Added `scraper_fetch()` as the single canonical HTTP entry point — it raises `the fixture-mode network guard error` under fixture mode and delegates to httpx under live/record. Documented the retailer fixture path convention under `backend/test/` with required scenarios (`in_stock`, `out_of_stock`, `multi_variant`; generic adds `jsonld_friendly`, `og_only`, `no_extractable_data`). Tests cover contract validation, mode parsing including the CI-default assertion, registry lookup semantics, fixture loader read/write/atomicity, the fixture-mode network block, and that no scraper module except `http.py` imports an HTTP client.

**Files:** `backend/scrapers/__init__.py`, `backend/scrapers/contract.py`, `backend/scrapers/mode.py`, `backend/scrapers/exceptions.py`, `backend/scrapers/registry.py`, `backend/scrapers/fixture_loader module`, `backend/scrapers/http.py`, `backend/scrapers/README.md`, `backend/test/conftest.py`, `backend/test/.../retailers/_example_retailer/` HTML and JSON fixture files, `backend/test/test_scraper_contract.py`, `backend/test/test_scraper_mode.py`, `backend/test/test_scraper_registry.py`, `backend/test/test_fixture_loader.py`, `backend/test/test_scraper_http_guard.py`, `backend/test/test_fixture_convention.py`, `docs/ROADMAP.md`, `MEMORY.md`.

**Deferred:** generic retailer registration and JSON-LD/OG extraction → T2.2; `bestbuy_ca` registration and real retailer fixture files → T2.3; benchmark-recorded `default_strategy` per retailer → T5.1; weekly drift-detection workflow that calls `FixtureLoader.record` → T5.5.

## [2026-06-14] T1.2 backend settings, clients, and auth dependency

**What:** Centralized backend settings via pydantic-settings, structured JSON logging, Supabase JWT validation (JWKS) with local auth-bypass dev dependency, worker-token guard for internal jobs, and service-role Supabase client wrapper refactored off bare `os.getenv`.

**Files:** `backend/core/settings.py`, `backend/core/logging.py`, `backend/core/auth.py`, `backend/core/security.py`, `backend/db/supabase_client.py`, `backend/main.py`, `backend/requirements.txt`, `backend/test/test_settings.py`, `backend/test/test_auth.py`, `backend/test/test_worker_token.py`, `backend/test/test_logging.py`, `docs/AUTHENTICATION.md`, `docs/ROADMAP.md`, `MEMORY.md`.

**Deferred:** wiring `get_current_user` / `require_worker_token` onto real routes (T2.1, T2.5, T3.5).

## [2026-06-14] T1.2 review pass

**What:** Restored readable settings defaults (`Literal` scraper mode, exported constants), narrowed JWT decode exception handling, added invalid-`sub` UUID guard + test, updated stale auth-bypass doc text.

**Files:** `backend/core/settings.py`, `backend/core/auth.py`, `backend/test/test_settings.py`, `backend/test/test_auth.py`, `docs/AUTHENTICATION.md`, `MEMORY.md`.

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
