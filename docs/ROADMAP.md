# Shopping Monitor V1 Development Roadmap

> **Status:** Agent handoff roadmap for the V1 PRD.
> **Source of truth:** `docs/PRD.md` remains the product requirements source. This roadmap translates it into a dependency-aware implementation sequence for parallel AI agents and just-in-time human setup.
> **Last updated:** 2026-06-15 (T8.6 manual product rename on detail page).

---

## 1. Operating principles for agents

Use this roadmap before opening feature branches. The goal is to reach a reliable MVP for one retailer (`bestbuy_ca`) first, validate it once against a real Best Buy Canada URL, and only then fan out to the remaining V1 retailers and polish work.

### Branch and PR rules

- Create branches from `main` using `cursor/<descriptive-name>-f127`.
- Prefer one PR per task when the task has a clean verification boundary.
- A larger PR is acceptable only when the changes are small, repeatable, and covered by end-to-end or integration-style tests proving the combined behavior works.
- Avoid editing the same files across parallel PRs when possible. Shared contracts should land before downstream feature work.
- Every PR must explain:
  - Which roadmap task(s) it completes.
  - How it was verified.
  - Any human setup that was required.
  - Any deferred work or fixture/live-mode limitation.

### Verification expectations

- Backend Python commands must run inside `backend/venv` when available.
- CI and local automated tests must default to `SCRAPER_MODE=fixtures`.
- New backend behavior needs focused pytest coverage.
- New frontend behavior needs Vitest/Testing Library coverage; add browser/e2e coverage once an e2e framework is introduced.
- Scraper work must include fixtures and tests that run with no outbound retailer requests.
- Live retailer validation is reserved for explicit benchmark, drift-check, fixture-recording, or final vertical-slice verification tasks.
- Schema PRs must include migrations, RLS, indexes, docs updates, and migration-validator coverage.

### Human approval boundaries

Agents may do small read-only/admin tasks and routine migration/application steps through the Supabase MCP when available. Ask for explicit human confirmation before destructive or high-blast-radius work, including:

- Deleting Supabase projects, auth users, production data, or remote resources.
- Rotating or exposing secrets.
- Enabling production schedules that send emails or hit live retailers repeatedly.
- Irreversible account-delete tests against real users.

---

## 2. Milestones

| Milestone | Status | Definition of done | Unlocks |
| --- | --- | --- | --- |
| M0: Planning baseline | done | Roadmap exists, linked from agent docs. | Agents can pick scoped tasks safely. |
| M1: Foundation | done | Schema, auth primitives, app shell, service interfaces, and fixture harness contracts exist. | Product flows and scraper work can proceed in parallel. |
| M2: First local vertical slice | done | A signed-in dev user can add, view, refresh, archive, restore, delete, and categorize a fixture-backed `bestbuy_ca` product locally. | Discovery, notifications, settings, currency, and more UI polish can fan out. |
| M3: Real Best Buy validation | done | The first slice works once against a live Best Buy Canada URL in controlled `live` or `record` mode. | Call the one-retailer MVP technically proven. |
| M4: MVP product workflows | done | Notifications, digest, currency, settings, account deletion, and review queues work against fixtures. **Done:** discovery/review (T3.1–T3.2), notification read API + evaluators on manual refresh (T3.3–T3.4), display currency (T4.1), scheduled scrape job (T3.5), digest email (T3.6), settings UI (T4.2), account delete (T4.3). | Deployment hardening and broader retailer expansion. |
| M5: V1 retailer coverage | done | Supported retailers have benchmark decisions, scraper modules, fixtures, and local drift checks (T5.1–T5.5). Deferred: `sportchek`, `footlocker_ca`, `costco_ca`, etc. | V1 success criteria can be tested end-to-end. |
| M6: Production-ready V1 | in progress | Deployed frontend/backend, scheduled jobs, Lighthouse/accessibility targets, 7-day scrape reliability check. **Progress:** T6.3 cron schedules; T6.2 production smoke; T7.1 UI polish; T7.4 auto-categorization UX shipped. **Remaining:** T6.4 7-day reliability, T7.2 Lighthouse, T7.3 checklist. | Invite early friends for feedback. |
| M8: Search-based product addition | done | Header search trigger (⌘K), `/api/search` LLM-grounded endpoint with 24h cache, `discovery_seed` plumbed through product creation, fixture-mode LLM provider, command-palette dialog with link-only unsupported-retailer support. | Lowers friction for new adds; supersedes "URL paste only" non-goal in PRD v1.4. |

---

## 3. Just-in-time human setup checklist

Do these only when the corresponding phase needs them.

| Checkpoint | Status | Unblocks |
| --- | --- | --- |
| H1 Supabase secrets | done | Schema, auth, integration tests |
| H2 Google OAuth | done | Live sign-in |
| H3 Gemini API key | done | Live LLM categorization/discovery smoke |
| H4 Resend | **done** | T3.6 digest live send verification |
| H5 Render, Vercel, GitHub Actions | **done** | T3.5/T6 `workflow_dispatch` against deployed backend |

### H1. Supabase project and local secrets

**Status:** done.

Needed before M1 schema/auth work can be fully verified against a real database.

- Create or select the Supabase project.
- Provide `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` in local/cloud-agent secrets.
- Let agents use the Supabase MCP for non-destructive project inspection, SQL migration application, and read-only/admin checks.
- Confirm before agents delete data or users.

### H2. Google OAuth

**Status:** done.

Needed before M2 auth UI can be considered complete.

- Create/configure Google OAuth credentials.
- Enable Google as the only Supabase Auth provider.
- Add local and deployed redirect URLs as they become known.
- V1 allows anyone with a Google account to sign in; no allowlist.

### H3. Gemini API key

**Status:** done.

Needed before live LLM categorization/discovery verification.

- Create a Gemini API key using the current Flash-family free-tier model.
- Add `GEMINI_API_KEY` to backend secrets.
- Agents should keep heuristic/fixture paths working without this key.

### H4. Resend

**Status:** done (2026-06-14) — sandbox account configured; `RESEND_API_KEY` available for local smoke and Render deploy.

Needed before digest delivery verification.

- Create a Resend account.
- Decide between sandbox sender and a verified domain for V1.
- Add `RESEND_API_KEY` to backend secrets.

### H5. Render, Vercel, and GitHub Actions secrets

**Status:** done (2026-06-14) — Render backend (`https://shopping-monitor-api.onrender.com`), Vercel frontend (`https://shopping-monitor-nine.vercel.app`), Supabase Auth redirect URLs, and GitHub Actions secrets (`BACKEND_BASE_URL`, `WORKER_TOKEN`) are configured. Scrape/digest cron schedules enabled in T6.3 (2026-06-15).

Needed before M6 production validation and T3.5 `workflow_dispatch` smoke against the deployed backend.

- Create Render backend service.
- Create Vercel frontend project.
- Add deployed URLs to Supabase Auth redirects.
- Add GitHub Actions secrets: `BACKEND_BASE_URL`, `WORKER_TOKEN`.
- Enable scheduled workflows after manual `workflow_dispatch` verification (done — T6.3).

---

## 4. Dependency map

```text
M0 roadmap
  -> F1 schema + RLS
  -> F2 auth/backend clients
  -> F3 frontend app shell
  -> F4 scraper contracts + fixtures mode

F1 + F2 + F3
  -> A1 auth/profile UI
  -> P1 product CRUD APIs

F4
  -> S1 generic scraper
  -> S2 bestbuy_ca fixture scraper
  -> S3 benchmark harness

P1 + S1 + S2 + A1
  -> V1 local Best Buy vertical slice
  -> V2 live Best Buy validation

Vertical slice
  -> D1 discovery
  -> N1 notifications
  -> C1 currency
  -> U1 settings
  -> R1 retailer expansion
  -> Q1 polish and quality gates

N1 + U1 + H4
  -> E1 digest email

All core workflows + H5
  -> DEP production rollout
```

---

## 5. Phase 0 — roadmap and coordination

### T0.1 Roadmap documentation

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/5.


- **Owner:** agent.
- **PR size:** single docs PR.
- **Files:** `docs/ROADMAP.md`, `README.md`, `MEMORY.md`, `.cursor/rules/project-memory.mdc`.
- **Verification:** docs render as Markdown; links are correct.

---

## 6. Phase 1 — foundations

These tasks should land before broad feature work. They are intentionally small enough to minimize merge conflicts.

### T1.1 Core database schema and RLS

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/8.


- **Owner:** agent, with Supabase MCP allowed for non-destructive application/checks.
- **Human setup:** H1.
- **PR size:** one PR is acceptable because the schema is tightly coupled, but keep it schema-only.
- **Files likely touched:** `backend/db/migrations/001_core_schema.sql`, `docs/DATABASE.md`, `scripts/check_migrations.py` tests if needed.
- **Build:**
  - Create `profiles`, `products`, `product_listings`, `price_history`, `notifications`, `fx_rates_cache`.
  - Enable RLS on every table in the same migration.
  - Add user-owned policies for Pattern A tables and no browser policies for backend-only `fx_rates_cache`.
  - Add enum-like check constraints, indexes, cascades, timestamp defaults, and `updated_at` trigger helper.
  - Include an advisory-lock helper function only if the internal job implementation needs a DB function.
- **Verification:**
  - `python scripts/check_migrations.py`.
  - Apply migration to a disposable Supabase project or dry-run via MCP where possible.
  - RLS smoke: authenticated user can access own rows and cannot access another user's rows.

### T1.2 Backend settings, clients, and auth dependency

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/11.


- **Owner:** agent.
- **Human setup:** H1 and H2 for live verification; local tests use auth bypass.
- **PR size:** single PR.
- **Files likely touched:** `backend/core/`, `backend/db/`, `backend/test/`.
- **Build:**
  - Central settings loader for Supabase, auth bypass, worker token, Gemini, Resend, app URL, scraper mode.
  - Service-role Supabase client wrapper.
  - Supabase JWT validation via JWKS.
  - `AUTH_BYPASS_ENABLED=true` local dependency using a fixed dev user UUID.
  - `require_worker_token` dependency for `/internal/jobs/*`.
  - Structured JSON logging helper.
- **Verification:**
  - Unit tests for settings defaults, auth bypass, missing/invalid bearer token, worker token acceptance/rejection.
  - Existing backend tests still pass.

### T1.3 Frontend app shell and shared dependencies

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/9.

- **Owner:** agent.
- **Human setup:** none for fixture/local mode.
- **PR size:** one PR; it will touch shared frontend files, so land before feature UI PRs.
- **Files likely touched:** `frontend/package.json`, `frontend/src/`, Tailwind/shadcn config files.
- **Build:**
  - Add Tailwind CSS, shadcn/ui setup, TanStack Query, react-router, Framer Motion, `sonner`, class utilities.
  - Create route layout: top nav, protected-route placeholder, dashboard/list/detail/notifications/history/settings route stubs, login route stub.
  - Add query client, API client wrapper, auth/theme/currency contexts.
  - Apply design defaults: light theme by default, calm monochrome base, skeleton primitives, toast outlet.
- **Verification:**
  - Frontend lint, tests, build.
  - Basic routing tests for route stubs and layout render.

### T1.4 Scraper contract and fixture mode harness

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/12.


- **Owner:** agent.
- **Human setup:** none.
- **PR size:** single backend PR.
- **Files likely touched:** `backend/scrapers/`, `backend/test/fixtures/retailers/`, `backend/test/`.
- **Build:**
  - Define `ProductSnapshot`, scraper exceptions, `ScraperMode`, scraper registry metadata, and `scrape(url) -> ProductSnapshot` contract.
  - Implement `FixtureLoader` for `fixtures`, `live`, and `record` mode stubs.
  - Enforce no outbound retailer requests in `fixtures` mode.
  - Add a generic fixture naming convention and helper tests.
- **Verification:**
  - Unit tests prove fixture mode reads local files and live mode is not used accidentally in CI.

### T1.5 Service interfaces

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/13.


- **Owner:** agent.
- **Human setup:** none.
- **PR size:** single backend PR, preferably after T1.2 and T1.4.
- **Build:**
  - Add interfaces/classes for `Categorizer`, `LlmProvider`, `FxService`, `MailService`, notification evaluator, and product price/trend helpers.
  - Include no-op/fake providers for tests.
- **Verification:**
  - Unit tests for interface-level fallback behavior where practical.

---

## 7. Phase 2 — auth/profile and first product slice

The tasks in this phase converge on the one-retailer MVP.

### T2.1 Auth and profile bootstrap

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/16.

- **Owner:** agent.
- **Human setup:** H1 and H2.
- **PR size:** single full-stack PR is acceptable if verified end-to-end; otherwise split backend profile endpoints and frontend login UI.
- **Build:**
  - Frontend Google login/logout using Supabase client.
  - Backend `GET /api/profile`, `PATCH /api/profile`.
  - Profile upsert on first authenticated API call or explicit bootstrap endpoint.
  - Route protection and session persistence.
- **Verification:**
  - Backend tests for profile defaults and update validation.
  - Frontend tests for login route states and protected-route behavior.
  - Manual local auth-bypass flow.
  - Live Google OAuth smoke once H2 is complete.

### T2.2 Generic JSON-LD/OG scraper

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/17.

- **Owner:** agent.
- **Human setup:** none.
- **PR size:** single backend PR.
- **Build:**
  - Parse schema.org Product JSON-LD first.
  - Fall back to OpenGraph/product meta tags.
  - Reject non-CAD listings with user-friendly error metadata.
  - Fixture coverage: JSON-LD-friendly, OG-only, and no-price site.
- **Verification:**
  - Fixture-only pytest coverage for title, image, price, currency, stock, and blocked/no-price paths.

### T2.3 `bestbuy_ca` fixture-backed scraper

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/18.

- **Owner:** agent.
- **Human setup:** one-time live fixture recording (3 Best Buy Canada product URLs).
- **PR size:** single backend PR.
- **Build:**
  - Add retailer registry entry for `bestbuy_ca`.
  - Implement fixture-backed extraction for title, brand, image, CAD price, stock, available variants, selected variant, breadcrumbs, snapshot.
  - Fixtures: in-stock, out-of-stock, multi-variant (recorded from live pages).
  - `curl_cffi` browser impersonation in `scraper_fetch()` for live/record mode.
- **Verification:**
  - Fixture-only pytest coverage.
  - Registry tests route `bestbuy.ca` URLs to `bestbuy_ca`.

### T2.4 Categorization service

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/19.

- **Owner:** agent.
- **Human setup:** H3 only for live Gemini smoke; tests use fakes.
- **PR size:** single backend PR.
- **Build:**
  - Manual category override path.
  - Gemini Flash `LlmProvider.categorize(...)` with 1.5s timeout and strict JSON slug response.
  - Heuristic fallback: retailer default, breadcrumbs, title/brand keywords, then `other`.
  - Return `category` + `category_source` on `CategorizationResult` (DB persistence → T2.5).
- **Verification:**
  - Unit tests for manual override, valid LLM, timeout, invalid slug, quota/error fallback, final `other`.

### T2.5 Product API vertical slice

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/20.

- **Owner:** agent.
- **Human setup:** H1.
- **PR size:** likely one backend PR; keep frontend out to reduce conflicts.
- **Build:**
  - `POST /api/products`
  - `GET /api/products`
  - `GET /api/products/:id`
  - `PATCH /api/products/:id`
  - `DELETE /api/products/:id`
  - `POST /api/products/:id/refresh`
  - `POST /api/products/:id/select-variant`
  - Product/listing creation, first price snapshot, archive/restore/delete, category/threshold updates, 1h refresh cooldown.
  - Product-level daily-min and trend helper.
  - Discovery enqueue via BackgroundTasks (implemented in T3.1).
- **Verification:**
  - Backend tests with fake scraper and fake Supabase/repository layer where possible.
  - If repository abstraction is thin, integration-marked tests can hit Supabase separately; unit tests must still run without Supabase.

### T2.6 Product frontend vertical slice

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/21.

- **Owner:** agent.
- **Human setup:** H1/H2 for live auth; local auth-bypass acceptable.
- **PR size:** one full frontend PR after T1.3 and T2.5 land.
- **Build:**
  - Add Product modal with URL input and category dropdown defaulting to Auto.
  - Dashboard grouped by category.
  - Flat list view with category/retailer/needs-review filters.
  - Product detail page with listings, threshold edit, category edit, refresh, archive/delete.
  - `/history` archived products view with restore and delete (PRD U-ARC-1–4).
  - Variant picker route for `needs_input`.
  - Optimistic mutations, skeletons, toasts, monochrome trend chip.
  - Playwright scaffold + optional live API integration test.
- **Verification:**
  - Vitest/Testing Library coverage for add modal, grouping, detail mutation controls, archive/delete/restore flows with mocked API.
  - Playwright happy-path spec + CI e2e job (T2.7).

### T2.7 Local end-to-end one-retailer slice

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/22.

- **Owner:** agent.
- **Human setup:** H1/H2 optional if using local auth bypass; required for full auth test.
- **PR size:** test-only/small wiring PR.
- **Build:**
  - Expand e2e coverage beyond T2.6 scaffold (add → detail → refresh → category/threshold → archive toast on current page → history via nav → restore → UI delete).
  - Wire CI job for Playwright; document `make test-e2e`.
- **Verification:**
  - E2E test passes in `SCRAPER_MODE=fixtures`.
  - Backend/frontend unit suites pass.

### T2.8 Controlled live Best Buy validation

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/23.

- **Owner:** agent with human awareness.
- **Human setup:** H1/H2; optionally H3 if categorization live path is included.
- **PR size:** docs/test artifact PR only if code changes are needed. Otherwise record result in `MEMORY.md`.
- **Build:**
  - Run one explicit `live` or `record` scrape against a real Best Buy Canada URL.
  - If live extraction needs `curl_cffi` or Playwright, implement the minimum measured fallback in a focused PR with tests and fixture updates.
  - Capture a fixture from the successful page if `record` mode is used.
- **Verification:**
  - One real Best Buy URL creates a product with current price and stock.
  - Fixture-mode tests remain the default and still pass.
- **Notes:** HTML PDP requests returned Akamai 403 from the agent VM; live scrape succeeded via Best Buy JSON product API fallback (`ScrapeSource.HTTP_PARSE`). Fixture `switch_2_in_stock` recorded as JSON-LD HTML synthesized from API payload plus raw `.json` snapshot. Tier A/B/C re-verified locally with live Gemini (`category_source=llm`).

---

## 8. Phase 3 — comparison and notification workflows

These can proceed after the local vertical slice lands.

### T3.1 Cross-retailer discovery engine

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/25

- **Owner:** agent.
- **Human setup:** H3 for live LLM smoke.
- **PR size:** full-stack PR (+ embedded `dimemtl` scraper for fixture-mode cross-retailer validation).
- **Build:**
  - `LlmProvider.discover(...)` with bounded prompt and up to 8 candidates.
  - Candidate scraping through registry.
  - Confidence scoring: title token Jaccard, brand exact match, variant exact match (no pHash; renormalized weights).
  - Auto-add, needs-review, discard, cap at 5 listings total.
  - BackgroundTasks orchestration and `discovery_complete` notification (only when ≥1 match added/queued).
  - Frontend polling: product detail 3s / list 5s while discovery in flight.
- **Verification:**
  - Unit tests with fake LLM and fake scrapers for auto-add/needs-review/discard/cap/failure.
  - `dimemtl` fixture scraper enables two-retailer fixture discovery path.

### T3.2 Listing review API and UI

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/26

- **Owner:** agent.
- **PR size:** single full-stack PR if T3.1 is stable.
- **Build:**
  - `POST /api/products/:id/listings/:listing_id/accept`
  - `POST /api/products/:id/listings/:listing_id/reject`
  - `DELETE /api/products/:id/listings/:listing_id`
  - Product detail "Needs review" queue with accept/reject/open-source actions.
  - Rejected and needs-review rows hidden from main listings table; Remove on confirmed matches.
  - Truncated `discovery_justification` in scrape snapshot for review reason display.
- **Verification:**
  - Backend tests for ownership, status transitions, cap semantics, serialized review fields.
  - Frontend Vitest for review queue, accept/reject, remove, and fallback copy.

### T3.3 Notification API and in-app bell

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/27.

- **Owner:** agent.
- **PR size:** single full-stack PR.
- **Build:**
  - `GET /api/notifications`
  - `POST /api/notifications/mark-read`
  - `POST /api/notifications/:id/action`
  - Bell nav unread count.
  - Notifications page sorted newest-first.
  - Revisit `keep` and `archive` actions.
- **Verification:**
  - Backend tests for pagination, mark-read, ownership, product interaction timestamp updates.
  - Frontend tests for bell count and action controls.

### T3.4 Price-drop, stock, scrape-failing, and revisit evaluators

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/28.

- **Owner:** agent.
- **PR size:** backend PR.
- **Build:**
  - Price-drop trigger against 30-day max baseline and newest product-level daily min.
  - Back-in-stock transition detection.
  - Scrape-failing after 3 consecutive scheduled failures (manual refresh increments count but never emits).
  - Revisit-on-sale and revisit-stale triggers with 30-day debounce and stale/on-sale mutual exclusion.
  - Wired into `refresh_product()`; exports `run_post_scrape_evaluation` for T3.5.
- **Verification:**
  - Synthetic 90-day fixture test for revisit prompts per PRD success criterion.
  - Unit tests for debounce and notification-disabled cases.
  - `pytest -m "not integration"` — 356 passed.

### T3.5 Internal scrape job endpoint

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/31.

- **Owner:** agent.
- **Human setup:** H5 done for deployed `workflow_dispatch` smoke; cron `schedule` enabled in T6.3.
- **PR size:** backend PR plus thin workflow/scripts if ready.
- **Build:**
  - `POST /internal/jobs/scrape-all` (worker-token protected).
  - Postgres advisory lock (`002_scrape_job_advisory_lock.sql`).
  - Retry each listing up to 2 times with exponential backoff (`1s`, `2s`).
  - Write `price_history` (`source='scheduled'`), update listing status, invoke scrape-triggered evaluators for touched products only, then revisit-only evaluators per user active products.
  - Thin `backend/workers/scrape_all.py` script.
  - `.github/workflows/scrape.yml` with `workflow_dispatch`; cron enabled in T6.3.
- **Verification:**
  - `ruff check .`, `pytest -m "not integration"` with `SCRAPER_MODE=fixtures`.
  - Worker script test/mocked HTTP call.
  - Migrations `001` + `002` applied on production Supabase.
  - Production `workflow_dispatch` verified — [run #27509008501](https://github.com/rudy-patel/shopping-monitor/actions/runs/27509008501) (2026-06-14).

### T3.6 Digest email service and job

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/35

- **Owner:** agent.
- **Human setup:** H4 done (Resend sandbox; live smoke recipient `rutvik@ualberta.ca`).
- **PR size:** backend PR.
- **Build:**
  - Resend-backed `MailService` behind interface.
  - Plain text + simple HTML digest templates.
  - `POST /internal/jobs/send-digests`.
  - Mark included notifications with `email_sent_at`.
  - Thin `backend/workers/send_digests.py`.
  - `.github/workflows/digest.yml` with `workflow_dispatch`; cron `schedule` enabled in T6.3.
- **Verification:**
  - Unit tests for no-unread suppression, email-disabled suppression, noop skip counting, rendered template contents, marking sent.
  - Sandbox live send smoke with H4 complete (`scripts/smoke_resend_digest.py --live`); production digest `workflow_dispatch` verified in T6.2 ([run #27513581095](https://github.com/rudy-patel/shopping-monitor/actions/runs/27513581095)).

---

## 9. Phase 4 — settings, currency, account lifecycle

### T4.1 FX rates and display currency

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/29.

- **Owner:** agent.
- **PR size:** single full-stack PR.
- **Build:**
  - Frankfurter primary (`api.frankfurter.dev/v1`) and ExchangeRate-API Open Access fallback (`open.er-api.com/v6`).
  - 24h cache in `fx_rates_cache`.
  - `GET /api/fx/rates`.
  - Header currency switcher for CAD/USD/EUR/GBP with profile sync.
  - Frontend conversion display only; CAD remains canonical for all stored values and thresholds.
- **Verification:**
  - Backend tests for cache hit/miss/provider failure.
  - Frontend tests for display conversion, CAD fallback, and profile sync.

### T4.2 Settings page

**Status:** done

- **Owner:** agent.
- **PR size:** frontend-heavy full-stack PR.
- **Build:**
  - Display currency (settings-only; header switcher removed).
  - Global notifications on/off.
  - Default threshold.
  - Email digest on/off.
  - Light/dark theme toggle with profile sync.
  - Revisit prompt toggles and `revisit_stale_days`.
  - Delete-account section enabled in T4.3 (`DELETE /api/account` + confirmation dialog).
- **Verification:**
  - Backend profile validation tests (existing).
  - Frontend Vitest for settings persistence and theme class.
  - Playwright theme persistence across reload.

### T4.3 Delete account

**Status:** done

- **Owner:** agent with human confirmation before destructive live test.
- **PR size:** focused backend/frontend PR if not completed in T4.2.
- **Build:**
  - `DELETE /api/account`.
  - Delete user's products/listings/history/notifications/profile in one transaction or ordered cascade.
  - Call Supabase Auth admin API to delete auth user.
  - Frontend confirmation flow.
- **Verification:**
  - Backend tests with mocked Supabase admin client.
  - Integration test with disposable admin-created users (local Supabase only).
  - Production disposable-user smoke verified in T6.2 (`smoke_delete_account.py --live --confirm`).

---

## 10. Phase 5 — retailer expansion and drift detection

Start after M3 proves the one-retailer architecture.

### T5.1 Benchmark harness

**Status:** done

- **Owner:** agent.
- **PR size:** backend tooling PR.
- **Build:**
  - CLI/script to run representative URLs through structured data, `curl_cffi` + parser, and Playwright where installed.
  - Record success/failure by title, price, stock, image, variants, runtime, retries, blocked markers.
  - Output recommended strategy/fallback order per retailer.
- **Verification:**
  - Fixture-mode benchmark tests (`backend/test/test_benchmark_harness.py`).
  - `make benchmark-retailers` → `docs/benchmarks/fixtures-*.json`.
  - Document command and output format (`docs/benchmarks/README.md`, `backend/scrapers/README.md`).
  - PR https://github.com/rudy-patel/shopping-monitor/pull/38

### T5.2 Easy Shopify/scrape-friendly retailers

**Status:** done

- **Owner:** agent (single PR on branch `cursor/t5.2-shopify-retailers-f127`).
- **Retailers shipped:** `palmisleskate` (`palmisleskateshop.com`), `tikiroomskate` (`tikiroomskateboards.com`).
- **Deferred post-MVP:** `eatyourwater` (AUD-only `.com.au`; PRD `.com` inactive).
- **Removed:** `dimemtl` (T3.1 enabler retired; discovery tests use palmisle/tikiroom fixtures).
- **Build:** shared `scrapers/shopify.py` + `scrapers/extraction/shopify.py` (JSON-LD/OG + theme meta variants), live-recorded fixtures, `scripts/record_shopify_fixtures.py`, benchmark catalog update.
- **Verification:** fixture-only pytest for each retailer; `make benchmark-retailers`; 470 backend unit tests.

### T5.3 Moderate retailers

**Status:** done

- **Owner:** single sequential PR (aligned with T5.2).
- **Retailers shipped:** `indigo` (`indigo.ca`), `apple_ca` (`apple.com/ca`), `abercrombie` (`abercrombie.com/shop/ca`).
- **Deferred:** `costco_ca`, `oakley`, `canadiantire`, `vans_ca` (bot protection / low ROI for V1).
- **Build:** shared `scrapers/structured_retailer.py` + retailer parsers, live-recorded fixtures, `scripts/record_retailer_fixtures.py`, benchmark catalog (+9 entries).
- **Verification:** fixture pytest per retailer; `make benchmark-retailers`; 485 backend unit tests.

### T5.4 Bot-protected retailers

**Status:** done

- **Owner:** single sequential PR (aligned with T5.3).
- **Retailers shipped:** `amazon_ca` (`amazon.ca`, 1P seller verification), `nike_ca` (`nike.com/ca`, `__NEXT_DATA__` parser).
- **Deferred:** `sportchek`, `footlocker_ca` — live `curl_cffi` returns bot/challenge shell HTML without extractable product data; production Playwright intentionally excluded per deployment policy.
- **Build:** shared `scrapers/bot_protected_retailer.py` HTTP-only factory, live-recorded fixtures, benchmark catalog (+6 entries), extended `record_retailer_fixtures.py`.
- **Verification:** fixture pytest per retailer; `make benchmark-retailers`; 500+ backend unit tests.

### T5.5 Drift detection workflow

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/44

- **Owner:** agent.
- **Human setup:** none for CI (local-only tool). Optional: `GITHUB_TOKEN` + `GITHUB_REPOSITORY` when using `--file-issues` locally.
- **PR size:** tooling PR (no GitHub Actions workflow — drift is not run on merge/CI).
- **Build:**
  - `backend/scrapers/drift/` module with live URL catalog, structural fingerprints, committed baselines.
  - `make update-drift-snapshots` (fixture-mode baseline regen) and `make check-retailer-drift` (live manual check).
  - Optional local `--file-issues` to open/update/close GitHub issues tagged `retailer-drift`.
- **Verification:**
  - Mocked drift pytest (`test_retailer_drift.py`); CI snapshot sync test (no live retailer requests).
  - Live smoke: `SCRAPER_MODE=live make check-retailer-drift` — 8/8 retailers ok (2026-06-15).

---

## 11. Phase 6 — deployment and production validation

### T6.1 Deployment docs and config hardening

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/34

- **Owner:** agent.
- **Human setup:** H5 done (infra live); aligned `docs/DEPLOYMENT.md` with configured Render/Vercel/Actions secrets and confirmed production URLs.
- **PR size:** docs/config PR.
- **Build:**
  - Rewrote `docs/DEPLOYMENT.md` with production reference table, env var matrix, Supabase redirects, scrape workflow + deploy-wait docs.
  - Synced `backend/.env.example` with `settings.py` (`CORS_ALLOWED_ORIGINS`, `LOG_LEVEL`, `GEMINI_DISCOVER_TIMEOUT_S`).
  - Migrations marked applied; Resend env vars documented (H4/T3.6 complete in follow-up PR #35).
- **Verification:** docs review; production health/OpenAPI/scrape checks in `docs/DEPLOYMENT.md`; `test_env_example_documents_settings_keys` guards `.env.example` sync.

### T6.2 Production smoke

**Status:** done — 2026-06-14

- **Owner:** agent with human coordination.
- **Human setup:** H1–H5 complete.
- **Verified:**
  - Google sign-in on deployed frontend (OAuth redirect + owner manual sign-in).
  - Live add/refresh on Render for `bestbuy_ca` (Switch 2, 2.6s, tech/llm) and `palmisleskate` (Bones Reds, 4.5s, other/heuristic); products cleaned up after smoke.
  - Digest `workflow_dispatch` suppression — [run #27513581095](https://github.com/rudy-patel/shopping-monitor/actions/runs/27513581095) (`mail_provider: resend`, `users_skipped_no_unread: 2`).
  - Account delete — `smoke_delete_account.py --live --confirm`.
  - Scrape pre-verified — [run #27509008501](https://github.com/rudy-patel/shopping-monitor/actions/runs/27509008501).
  - `frontend/vercel.json` SPA rewrite for direct `/login` deep links.
- **Script:** `backend/scripts/smoke_production_t6_2.py --live`.

### T6.3 Enable schedules

**Status:** done — 2026-06-15

- **Owner:** agent with explicit human confirmation.
- **PR size:** workflow PR.
- **Build:**
  - Enabled scrape cron `0 8 * * *` UTC in `.github/workflows/scrape.yml`.
  - Enabled digest cron `0 14 * * *` UTC in `.github/workflows/digest.yml`.
  - Workflow YAML guard tests in `backend/test/test_scheduled_workflows.py`.
- **Verification:**
  - `workflow_dispatch` scrape/digest smoke (T6.2 runs #27509008501, #27513581095).
  - Advisory lock skip on concurrent scrape (`lock_not_acquired` — `test_run_scrape_all_skipped_when_lock_not_acquired`).
  - Digest zero-unread suppression (`users_skipped_no_unread` — T6.2 + `test_digest_job_service`).
  - `pytest backend/test/test_scheduled_workflows.py`.

### T6.4 Seven-day reliability check

**Status:** pending

- **Owner:** human + agents.
- **Verify:**
  - Daily scrape runs 7 consecutive days.
  - At least 80% per-listing success rate across tracked products.
  - `scrape_failing` notifications make failures visible.
  - Record result in `MEMORY.md`.

---

## 12. Phase 7 — quality gates and V1 acceptance

### T7.1 UI polish and accessibility

**Status:** done — PR https://github.com/rudy-patel/shopping-monitor/pull/46

- **Owner:** agent.
- **PR size:** frontend PR.
- **Build:**
  - Text-only `ProductListRow` (no in-app images); category-grouped dashboard with sticky section headers.
  - Skeletons instead of spinners; refresh shows shimmer + “Refreshing…”.
  - Optimistic delete/archive/update; monochrome trend/stock chips with labels.
  - Mobile bottom tab bar, responsive filters, listing cards on detail, axe vitest suite.
  - Playwright Mobile Chrome project alongside Desktop Chrome.
  - Minimal bundled SVG retailer icons beside labels on list/detail/search surfaces (`frontend/src/assets/retailers/`, `RetailerLogo`); generic scraper listings stay text-only.
- **Verification:**
  - `npm run lint`, `npm run test:run`, `npm run build`, `npm run test:e2e` (both projects).
  - PRD U-VIEW-3/U-VIEW-4 updated for typography-first lists.

### T7.2 Lighthouse gate

**Status:** pending

- **Owner:** agent.
- **PR size:** optimization PR(s) if needed.
- **Verify:**
  - Dashboard and product detail hit Lighthouse Performance >= 95 and Accessibility >= 95 on desktop throttled run.
  - Document command/results in PR.

### T7.4 Auto-categorization UX polish

**Status:** done — 2026-06-15

- **Owner:** agent.
- **PR size:** frontend PR.
- **Build:**
  - Streamline Add Product modal (URL-first; manual category behind disclosure).
  - Product detail `CategoryField` thinking shimmer (~2.5s min) + "Sorted by AI" hint; override via existing select.
  - Dashboard `ProductListRow` "Sorting…" badge for the same just-added session window.
  - Session-scoped `just-added-product` helper in `frontend/src/lib/just-added-product.ts` (no extra LLM calls).
- **Verification:**
  - Vitest: `just-added-product.test.ts`, `category-field-thinking.test.tsx`, `product-list-row.test.tsx`, updated add-product dialog tests.
  - Playwright add flow waits for category thinking → select visible.
  - `npm run lint`, `npm run test:run`, `npm run build`, `make test-e2e`.

### T7.3 V1 success-criteria checklist

**Status:** pending

- **Owner:** agent.
- **PR size:** docs PR.
- **Build:**
  - Add a final checklist mapping `docs/PRD.md` §15 criteria to implemented verification artifacts.
  - Link tests, workflows, manual smoke notes, and known limitations.
- **Verification:** checklist review.

### T8.1 Search-based product addition (M8)

**Status:** done — 2026-06-15

- **Owner:** agent (single bundled PR per user request).
- **Branch:** `cursor/auto-categorization-ux-f127`.
- **Scope:** flip the add-product experience from URL-paste-only to search-first while keeping URL paste available.
- **Backend:**
  - Extended `LlmProvider` with a `search(query)` method (Gemini Flash + Google Search grounding); `NoOpLlmProvider`, `FakeLlmProvider`, and `FixtureLlmProvider` all implement it.
  - Added `search_cache` table (`backend/db/migrations/003_search_cache.sql`) + `SearchCacheService` with normalized query hashing and `SEARCH_CACHE_TTL_HOURS` (default 24h).
  - `POST /api/search` endpoint + `search_service` orchestrator: dedupe + Canadian-host filtering + supported-retailer classification + caching.
  - `POST /api/products` accepts optional `discovery_seed`; `run_discovery_for_product` skips the LLM when a seed is provided, and short-circuits for generic primary listings.
  - `FixtureLlmProvider` ships canned search responses (`backend/test/fixtures/search/*.json`) for fixtures mode so CI/local agents never hit Gemini.
- **Frontend:**
  - `SearchTrigger` + `SearchTriggerMobile` in the top nav; global ⌘K / Ctrl+K shortcut.
  - `SearchCommandDialog` (Radix dialog + Framer Motion staggered entry, skeleton loader, idle examples, link-only unsupported-retailer variant, inline Track action).
  - `useSearch` hook with TanStack Query keyed cache that matches the 24h server TTL.
  - `useCreateProduct` mutation passes `discovery_seed` straight through.
- **Tests:**
  - Backend: `test_services_gemini.py` (search method), `test_search_service.py`, `test_search_cache_service.py`, `test_search_router.py`, `test_migration_003_search_cache.py`, `test_llm_fixtures.py`; `test_discovery.py` + `test_products_router.py` covering `discovery_seed`.
  - Frontend: `search-trigger.test.tsx`, `search-dialog.test.tsx`, and `top-nav.test.tsx` updates.
  - Manual: `python backend/scripts/smoke_search_live.py --live "AirPods Pro"` (gated by `GEMINI_API_KEY`).
- **Docs:** PRD v1.4 (§4 scope, §5.2 U-ADD-0, §6 IA, §8.7 `search_cache`, §9 API surface, §10.7 LLM use cases + free-tier table); MEMORY.md entry.
- **Verification (local, in-Cursor browser):** Dashboard → ⌘K opens overlay → example query → results render with supported + unsupported badges → Track adds product and navigates to detail with thinking shimmer + listing populated.

### T8.4 Search quota + transient-error resilience (M8)

**Status:** done — 2026-06-15

- **Owner:** agent.
- **Scope:** unwedge production `/api/search` — every query was timing out at ~30s with "Search is temporarily unavailable", and no real search had succeeded in production since launch.
- **Root causes (stacked):**
  1. **Free-tier quota wall.** `gemini-2.5-flash` + `google_search` is capped at ~20 RPD/project on the free tier; that pool exhausted within minutes of normal use and every subsequent request returned `429 RESOURCE_EXHAUSTED`.
  2. **Quota errors were retried.** Backend retried 429 once (~1s sleep), router mapped quota to `503`, frontend treated 503 as transient and retried again. One user click → up to 4 cascaded failed Gemini calls with the spinner held the entire time.
  3. **Timed-out Gemini threads leaked.** `ThreadPoolExecutor` was never shut down after `LlmTimeoutError`; the SDK thread kept running past the user-visible timeout.
- **Backend:** new `GEMINI_SEARCH_MODEL` setting defaulting to `gemini-2.5-flash-lite` (separate, much larger free-tier RPD pool; faster grounded responses). Distinct HTTP status codes — quota=`429`, transient=`503`, timeout=`504`, malformed=`502`. `_call_gemini_grounded` retries up to 3 attempts only on truly transient `500/502/503/504` errors and empty responses; **never** retries on quota. `search()` / `discover()` wrap the executor in `try/finally` with `pool.shutdown(wait=False, cancel_futures=True)`. Natural-language refusals (e.g. "I'm sorry, I can't…" on broad queries) degrade to empty results instead of 502. Per-attempt structured logs include model, elapsed_ms, finish_reason, text_len. New unauthenticated `GET /health/llm` reports config without burning quota.
- **Frontend:** `useSearch` stops retrying on 429 (`isQuotaExhaustedError`) and caps transient retries at exactly one (`SEARCH_RETRY_LIMIT = 1`). `SearchCommandDialog`'s `ErrorState` renders distinct copy for quota exhaustion (`search-quota-exhausted` testid: "Daily AI search limit reached…") vs. generic transient (`search-error`), both with **Add by URL** fallback so the user is never stuck.
- **Tests:** `test_grounded_search_does_not_retry_on_quota_error`, `test_grounded_search_retries_on_transient_503` / `_504` / `_on_empty_response`, `test_search_uses_search_model_not_default_model`, `test_search_model_falls_back_to_default_model`, `test_discover_uses_search_model_not_categorize_model`, `test_search_does_not_double_wrap_provider_error`, `test_search_natural_language_refusal_returns_empty_results`, `test_search_malformed_json_still_raises`, `test_search_provider_error_returns_503`, `test_search_quota_exhausted_returns_429`, `test_health_llm_returns_configured_models`, `test_settings` env-key + default coverage for `GEMINI_SEARCH_MODEL`; frontend `shows the daily-limit message (no transient-error retries) when Gemini quota is exhausted` + `retries once on transient 503 but stops there so the spinner does not linger` in `search-dialog.test.tsx`.
- **Docs:** PRD §10.7 (search-model split + retry/timeout policy + `/health/llm`) + §10.9 quota table; `DEPLOYMENT.md` (env matrix + verification curl); `AGENTS.md` (env var + corrected timeout default); `MEMORY.md` entry.
- **Deploy:** set `GEMINI_SEARCH_MODEL=gemini-2.5-flash-lite` (and optionally `GEMINI_SEARCH_TIMEOUT_S=20`) on Render. No migrations.
- **Verification (live in-Cursor browser):** "airpods pro" returned 5 results (Apple Canada, Best Buy Canada, Amazon Canada, Indigo, Costco Canada) in ~3.6s; `/health/llm` reports `search_model: "gemini-2.5-flash-lite"`.

### T8.2 Search production hotfix (M8)

**Status:** done — 2026-06-15 (second pass: timeout alignment)

- **Owner:** agent.
- **Scope:** fix production `/api/search` failures and improve in-flight search UX.
- **Root causes:**
  1. **502** — `gemini-2.5-flash` rejects `response_schema` + `google_search` together (`400 INVALID_ARGUMENT`); same pattern affected `discover()`.
  2. **504** — grounded Gemini often exceeds the interim `12.0`s search timeout; users saw "Search took too long" even after the grounding fix (#49).
- **Backend (#49):** grounded search/discovery prompt for JSON and parse locally (`_call_gemini_grounded`); interim `GEMINI_SEARCH_TIMEOUT_S` raised to `12.0`.
- **Backend (second pass):** default `GEMINI_SEARCH_TIMEOUT_S` raised to `30.0` (aligned with `GEMINI_DISCOVER_TIMEOUT_S`); `POST /api/search` runs `run_search` via `asyncio.to_thread`; `test_settings` documents `GEMINI_SEARCH_TIMEOUT_S` + `SEARCH_CACHE_TTL_HOURS`.
- **Frontend (#49):** `SearchThinking` component — rotating status copy + skeleton rows while `isFetching`.
- **Tests:** `test_search_grounded_call_omits_structured_output_config`, `test_discover_grounded_call_omits_structured_output_config`, `test_extract_json_text_strips_markdown_fence`, `search-thinking.test.tsx`, loading-state test in `search-dialog.test.tsx`; second pass adds default-timeout assertions in `test_settings` + `test_get_llm_provider_with_key`.
- **Docs:** PRD §10.7 grounded-JSON note + timeout guardrails + risk rows; `DEPLOYMENT.md` migration 003 + timeout; `AGENTS.md`, `.env.example`, `MEMORY.md`.
- **Deploy:** backend Render redeploy required for fixes to reach production.

### T8.5 LLM-cleaned product titles on add (M8)

**Status:** ✅ done (combined with categorize call; zero added Gemini requests).

- **Backend:** `LlmCategorizationResult.clean_title` (4-80 chars, validated and silently dropped on bad output); `_GeminiCategoryPayload` extended; `categorize` prompt updated with three concrete shortening examples; `DefaultCategorizer` propagates `clean_title` only on the LLM path; fixture provider runs deterministic separator-split shortening so fixture-mode dev sees the same UX. `product_service._pick_display_title` adopts the cleaned title only when strictly shorter than the scraped title (and not equal case-insensitive). Original scraped title preserved verbatim in `product_listings.scrape_snapshot.title`.
- **Frontend:** No code change — `product.title` flows through unchanged into all surfaces.
- **Tests:** `test_services_gemini.py` (clean_title parsing + length-bound rejection + inclusive-boundary lock), `test_services_categorizer.py` (propagation + manual-override / heuristic skipping), `test_llm_fixtures.py` (separator-split + already-concise pass-through), `test_products_router.py` (router-level adoption + scraped-title equality short-circuit), new `test_product_service_clean_title.py` for the `_pick_display_title` policy.
- **Docs:** PRD §5.2 U-ADD-9, §7.7 categorization waterfall, §10.7 LLM use case 3 retitled "Categorization + title cleanup"; `backend/services/README.md`; `MEMORY.md`.
- **Free-tier guardrail:** zero added Gemini requests per add — both `category` and `clean_title` ride a single structured-JSON `gemini-2.5-flash` call. Validated against ~1,500 RPD non-grounded free-tier ceiling and PRD §10.9's ~30 adds/day budget.
- **Second-pass cleanup:** centralized `MIN_CLEAN_TITLE_LEN`/`MAX_CLEAN_TITLE_LEN` in `services/llm.py` (single source of truth, removed dupes from `gemini.py` + `llm_fixtures.py`); collapsed `test_product_service_clean_title.py` to two parametrized tests; added inclusive-boundary lock for the 4 / 80 char limits; updated `scripts/smoke_gemini_categorize.py` to print `clean_title` and use a verbose seed title that exercises the live-LLM shortening path.

**Deferred:** retroactive backfill of cleaned titles for existing products (would require an opt-in worker that re-calls categorize per row, ≈1 Gemini request per backfilled product). Not blocking V1 — users can rename from the product detail page (T8.6).

### T8.6 Manual product rename (M8)

**Status:** ✅ done.

- **Backend:** `PATCH /api/products/{id}` accepts optional `title` (1–200 chars, trimmed); stored on `products.title`; refresh/scrape does not overwrite manual names.
- **Frontend:** inline **Rename** control on product detail hero (`ProductTitleField`); uses existing `useUpdateProduct` optimistic cache updates.
- **Tests:** router PATCH title validation; product detail unit tests; e2e step in `products.spec.ts` lifecycle.
- **Docs:** PRD U-VIEW-5b; `MEMORY.md`.

---

## 13. Suggested parallel agent lanes

Use these lanes after the foundation tasks land. Keep each lane on separate files/modules as much as possible.

| Lane | Starts after | Agent focus | Avoid conflicts with |
| --- | --- | --- | --- |
| Backend schema/auth | T1.1 | T1.2, T2.1 backend | Product API until auth contracts settle |
| Frontend shell | T1.3 | Layout, routes, auth UI, settings UI | Product UI until API contracts settle |
| Scrapers | T1.4 | Generic, Best Buy, benchmark, retailer modules | Product API only via scraper contract |
| Product API | T1.1/T1.2/T1.4 | Products, listings, refresh, trends | Discovery/notifications until base endpoints land |
| Product UI | T1.3/T2.5 | Dashboard, list, detail, add modal | Settings and notifications routes |
| Discovery | T2.5/T2.8 | LLM discovery and review queue | Retailer modules except through registry |
| Notifications/jobs | T2.5 | evaluators, internal jobs, digest | Product API helpers and notification UI contracts |
| Deployment | M4 | Render/Vercel/GitHub Actions docs and smoke | T6.4 reliability monitoring |

---

## 14. Agent handoff prompt template

Copy this when launching an agent:

```text
Read @MEMORY.md, @docs/PRD.md, @docs/ROADMAP.md, and @AGENTS.md first.

Implement roadmap task <TASK ID + title>.

Constraints:
- Branch from main as cursor/<descriptive-name>-f127.
- Keep SCRAPER_MODE=fixtures for automated tests unless this task explicitly calls for live/record mode.
- Do not hit live retailers unless the task explicitly requires benchmark, record, drift, or final live validation.
- Any new public Supabase table must enable RLS in the migration.
- Update docs and MEMORY.md if behavior or project history changes.
- Include tests or an explicit verification artifact; everything must be verifiable.
- Before committing, summarize git diff and wait for the user's commit message approval if the user has that rule enabled.
```

---

## 15. Near-term recommended execution order

**Phase 3 through T3.6, Phase 4 through T4.3, deployment docs (T6.1), T5.1–T5.5 retailer expansion + drift tooling, T6.2 production smoke, and T6.3 cron schedules are complete.** Pick next from:

1. **T6.4** Seven-day scrape reliability check.
2. **T7.2** Lighthouse gate.
3. **T7.3** V1 success-criteria checklist.

<details>
<summary>Recently completed (M8)</summary>

- ~~**T8.6** Manual product rename~~ — inline **Rename** on product detail hero; `PATCH /api/products/{id}` accepts `title` (1–200 chars); manual names persist through refresh/scrape (PRD U-VIEW-5b).
- ~~**Dashboard category UX**~~ — collapsible Notion-style category toggles; all five categories visible (empty ones collapsed at 0); **Edit order** mode for category-section and within-category product drag-reorder (`dashboard_sort_order` + `PUT /api/products/dashboard-order`; category order in localStorage). Flat list view (`/list`) keeps `created_at` desc — manual order applies only on the grouped dashboard (PRD U-VIEW-1).
- ~~**T8.5** LLM-cleaned product titles on add~~ — `clean_title` returned alongside `category` from the same Gemini Flash structured-JSON call (zero added requests). Adopted only when strictly shorter than the scraped title; original scraped title preserved on the listing. Fixture-mode shortener mirrors the live UX for local dev.
- ~~**T8.4** Search quota + transient-error resilience~~ — switched grounded calls to `gemini-2.5-flash-lite` (separate free-tier RPD pool from Flash), split error mapping (quota → 429, transient → 503, timeout → 504), retry only on transient errors / empty responses, never on quota; non-leaking executor shutdown; graceful refusal handling; distinct frontend copy for quota vs transient with Add-by-URL fallback; new `/health/llm` diagnostic endpoint.
- ~~**T8.2** Search production hotfix~~ — Gemini grounded JSON parsing fix (#49), `SearchThinking` loading UX, 30s search timeout + `asyncio.to_thread` second pass.
- ~~**T8.1** Search-based product addition~~ — `POST /api/search` + 24h cache, `discovery_seed` plumbing, ⌘K command palette dialog, fixture-mode LLM provider.

</details>

<details>
<summary>Recently completed (M6 / T7)</summary>

- ~~**Product detail back navigation**~~ — `BackLink` with arrow icon and aligned placement on product detail (loading, not-found, active, archived).
- ~~**Product detail hero + 30-day sparkline**~~ — hero best price (trend-tinted) + retailer; unified `[best price] [chip] [sparkline]` row; `GET /api/products/:id` now returns `price_history_30d` daily-min series; backfill at current best for new products (PRD §5.3 U-VIEW-4).
- ~~**Product detail listings polish (Tier 2)**~~ — cheapest-first cards, subtle best-price highlight, `+$N vs best` deltas, tighter card hierarchy (large price, retailer + stock on one line), scrape status hidden from cards (PRD §5.3 U-VIEW-4, §5.4 U-CMP-4).
- ~~**Product detail layout & micro-copy (Tier 3–4)**~~ — hero card, collapsible Settings, metadata chips, mobile sticky price+trend, threshold dollar hint, enriched trend chip, archived sparkline pause state (PRD §5.3 U-VIEW-4, U-VIEW-6).
- ~~**Listing card retailer link**~~ — retailer label beside the logo links to the source URL (external-link icon, new tab); removed separate "Open on …" row (PRD §5.3 U-VIEW-4, §5.4 U-CMP-2).
- ~~**Archive in-context feedback**~~ — success toast on archive; no auto-redirect to `/history` (PRD U-ARC-1).
- ~~**T7.4** Auto-categorization UX polish~~ — URL-first add modal, category thinking shimmer (~2.5s), dashboard sorting badge; client-side only (no extra Gemini calls).
- ~~**T7.1** UI polish and accessibility~~ — typography-first lists, mobile tab bar, axe vitest, Playwright Mobile Chrome.
- ~~**T6.3** Cron schedules~~ — scrape `0 8 * * *` UTC, digest `0 14 * * *` UTC.
- ~~**T6.2** Production smoke~~ — done.

</details>

<details>
<summary>Recently completed (M5 / M6)</summary>

- ~~**T5.5** Drift detection~~ — local `make check-retailer-drift` + `make update-drift-snapshots` (not run in CI).
- ~~**T5.4** Bot-protected retailers~~ — `amazon_ca`, `nike_ca` (deferred `sportchek`, `footlocker_ca`).
- ~~**T5.3** Moderate retailers~~ — `indigo`, `apple_ca`, `abercrombie`.
- ~~**T5.2** Easy Shopify retailers~~ — `palmisleskate`, `tikiroomskate`.
- ~~**T5.1** Benchmark harness~~ — done.
- ~~**T6.2** Production smoke~~ — done.
- ~~**T6.3** Cron schedules~~ — scrape `0 8 * * *` UTC, digest `0 14 * * *` UTC.

</details>

M4 validated in production (T6.2 done). M5 complete through T5.5. M8 search shipped; **T8.2** grounding + timeout fixes ready for Render deploy.

<details>
<summary>Historical bootstrap order (M0–M3, completed)</summary>

1. ~~T1.1 Core database schema and RLS.~~
2. ~~T1.2 Backend settings, clients, and auth dependency.~~
3. ~~T1.3 Frontend app shell and shared dependencies.~~
4. ~~T1.4 Scraper contract and fixture mode harness.~~
5. ~~T1.5 Service interfaces.~~
6. ~~T2.2 Generic JSON-LD/OG scraper and T2.3 `bestbuy_ca` fixture-backed scraper.~~
7. ~~T2.1 Auth and profile bootstrap.~~
8. ~~T2.4 Categorization service.~~
9. ~~T2.5 Product API vertical slice.~~
10. ~~T2.6 Product frontend vertical slice.~~
11. ~~T2.7 Local e2e one-retailer slice.~~
12. ~~T2.8 Controlled live Best Buy validation.~~
13. ~~T3.1 Cross-retailer discovery engine.~~
14. ~~T3.2 Listing review API and UI.~~
15. ~~T3.3 Notification API and in-app bell.~~
16. ~~T3.4 Notification evaluators and post-scrape orchestration.~~
17. ~~T3.5 Internal scrape job endpoint.~~
18. ~~T3.6 Digest email service and job.~~
19. ~~T4.1 FX rates and display currency.~~
20. ~~T4.2 Settings page.~~
21. ~~T6.1 Deployment docs and config hardening.~~

</details>
