# Shopping Monitor V1 Development Roadmap

> **Status:** Agent handoff roadmap for the V1 PRD.
> **Source of truth:** `docs/PRD.md` remains the product requirements source. This roadmap translates it into a dependency-aware implementation sequence for parallel AI agents and just-in-time human setup.
> **Last updated:** 2026-06-13.

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
| M2: First local vertical slice | pending | A signed-in dev user can add, view, refresh, archive, restore, delete, and categorize a fixture-backed `bestbuy_ca` product locally. | Discovery, notifications, settings, currency, and more UI polish can fan out. |
| M3: Real Best Buy validation | pending | The first slice works once against a live Best Buy Canada URL in controlled `live` or `record` mode. | Call the one-retailer MVP technically proven. |
| M4: MVP product workflows | pending | Notifications, digest, currency, settings, account deletion, and review queues work against fixtures. | Deployment hardening and broader retailer expansion. |
| M5: V1 retailer coverage | pending | Supported retailers have benchmark decisions, scraper modules, fixtures, and drift checks. | V1 success criteria can be tested end-to-end. |
| M6: Production-ready V1 | pending | Deployed frontend/backend, scheduled jobs, Lighthouse/accessibility targets, 7-day scrape reliability check, account-delete verification. | Invite early friends for feedback. |

---

## 3. Just-in-time human setup checklist

Do these only when the corresponding phase needs them.

### H1. Supabase project and local secrets

Needed before M1 schema/auth work can be fully verified against a real database.

- Create or select the Supabase project.
- Provide `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` in local/cloud-agent secrets.
- Let agents use the Supabase MCP for non-destructive project inspection, SQL migration application, and read-only/admin checks.
- Confirm before agents delete data or users.

### H2. Google OAuth

Needed before M2 auth UI can be considered complete.

- Create/configure Google OAuth credentials.
- Enable Google as the only Supabase Auth provider.
- Add local and deployed redirect URLs as they become known.
- V1 allows anyone with a Google account to sign in; no allowlist.

### H3. Gemini API key

Needed before live LLM categorization/discovery verification.

- Create a Gemini API key using the current Flash-family free-tier model.
- Add `GEMINI_API_KEY` to backend secrets.
- Agents should keep heuristic/fixture paths working without this key.

### H4. Resend

Needed before digest delivery verification.

- Create a Resend account.
- Decide between sandbox sender and a verified domain for V1.
- Add `RESEND_API_KEY` to backend secrets.

### H5. Render, Vercel, and GitHub Actions secrets

Needed before M6 production validation.

- Create Render backend service.
- Create Vercel frontend project.
- Add deployed URLs to Supabase Auth redirects.
- Add GitHub Actions secrets: `BACKEND_BASE_URL`, `WORKER_TOKEN`.
- Enable scheduled workflows only after manual `workflow_dispatch` verification.

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

**Status:** done


- **Owner:** agent.
- **PR size:** single docs PR.
- **Files:** `docs/ROADMAP.md`, `README.md`, `MEMORY.md`, `.cursor/rules/project-memory.mdc`.
- **Verification:** docs render as Markdown; links are correct.

---

## 6. Phase 1 — foundations

These tasks should land before broad feature work. They are intentionally small enough to minimize merge conflicts.

### T1.1 Core database schema and RLS

**Status:** done


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

**Status:** complete — PR https://github.com/rudy-patel/shopping-monitor/pull/11.


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

**Status:** complete — PR https://github.com/rudy-patel/shopping-monitor/pull/9.

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

**Status:** complete — PR https://github.com/rudy-patel/shopping-monitor/pull/12.


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

**Status:** complete — PR https://github.com/rudy-patel/shopping-monitor/pull/13.


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

**Status:** complete — PR https://github.com/rudy-patel/shopping-monitor/pull/16

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

**Status:** done

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

**Status:** done

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

**Status:** done

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

**Status:** done

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
  - Stub discovery enqueue via BackgroundTasks with `discovery_status='pending'` or a no-op completion until T4.1.
- **Verification:**
  - Backend tests with fake scraper and fake Supabase/repository layer where possible.
  - If repository abstraction is thin, integration-marked tests can hit Supabase separately; unit tests must still run without Supabase.

### T2.6 Product frontend vertical slice

**Status:** done

- **Owner:** agent.
- **Human setup:** H1/H2 for live auth; local auth-bypass acceptable.
- **PR size:** one full frontend PR after T1.3 and T2.5 land.
- **Build:**
  - Add Product modal with URL input and category dropdown defaulting to Auto.
  - Dashboard grouped by category.
  - Flat list view with category/retailer/needs-review filters.
  - Product detail page with listings, threshold edit, category edit, refresh, archive/delete (no restore UI until History).
  - Variant picker route for `needs_input`.
  - Optimistic mutations, skeletons, toasts, monochrome trend chip.
  - Playwright scaffold + optional live API integration test.
- **Verification:**
  - Vitest/Testing Library coverage for add modal, grouping, detail mutation controls, archive/delete flows with mocked API.
  - Playwright happy-path spec (local only; CI wiring in T2.7).

### T2.7 Local end-to-end one-retailer slice

**Status:** pending

- **Owner:** agent.
- **Human setup:** H1/H2 optional if using local auth bypass; required for full auth test.
- **PR size:** test-only/small wiring PR.
- **Build:**
  - Add e2e test path proving a dev user can add a fixture-backed Best Buy product, view it on dashboard, open detail, refresh, edit category/threshold, archive, restore, delete.
  - Document local e2e command.
- **Verification:**
  - E2E test passes in `SCRAPER_MODE=fixtures`.
  - Backend/frontend unit suites pass.

### T2.8 Controlled live Best Buy validation

**Status:** pending

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

---

## 8. Phase 3 — comparison and notification workflows

These can proceed after the local vertical slice lands.

### T3.1 Cross-retailer discovery engine

**Status:** pending

- **Owner:** agent.
- **Human setup:** H3 for live LLM smoke.
- **PR size:** backend PR.
- **Build:**
  - `LlmProvider.discover(...)` with bounded prompt and up to 8 candidates.
  - Candidate scraping through registry.
  - Confidence scoring: title token Jaccard, brand exact match, variant exact match, optional image pHash only if low complexity.
  - Auto-add, needs-review, discard, cap at 5 listings total.
  - BackgroundTasks orchestration and `discovery_complete` notification.
- **Verification:**
  - Unit tests with fake LLM and fake scrapers for auto-add/needs-review/discard/cap/failure.

### T3.2 Listing review API and UI

**Status:** pending

- **Owner:** agent.
- **PR size:** single full-stack PR if T3.1 is stable.
- **Build:**
  - `POST /api/products/:id/listings/:listing_id/accept`
  - `POST /api/products/:id/listings/:listing_id/reject`
  - `DELETE /api/products/:id/listings/:listing_id`
  - Product detail "Needs review" queue with accept/reject/open-source actions.
  - Exclude needs-review/rejected rows from best price/trend math.
- **Verification:**
  - Backend tests for ownership, status transitions, listing cap semantics.
  - Frontend tests for review queue behavior.

### T3.3 Notification API and in-app bell

**Status:** pending

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

**Status:** pending

- **Owner:** agent.
- **PR size:** backend PR.
- **Build:**
  - Price-drop trigger against 30-day max baseline and newest product-level daily min.
  - Back-in-stock transition detection.
  - Scrape-failing after 3 consecutive scheduled failures.
  - Revisit-on-sale and revisit-stale triggers with 30-day debounce and stale/on-sale mutual exclusion.
- **Verification:**
  - Synthetic 90-day fixture test for revisit prompts per PRD success criterion.
  - Unit tests for debounce and notification-disabled cases.

### T3.5 Internal scrape job endpoint

**Status:** pending

- **Owner:** agent.
- **Human setup:** H5 only when connecting GitHub Actions.
- **PR size:** backend PR plus thin workflow/scripts if ready.
- **Build:**
  - `POST /internal/jobs/scrape-all`.
  - Postgres advisory lock.
  - Retry each listing up to 2 times with exponential backoff.
  - Write `price_history`, update listing status, invoke notification/revisit evaluators.
  - Thin `backend/workers/scrape_all.py` script.
  - `.github/workflows/scrape.yml` with `workflow_dispatch`; add `schedule` only when production is ready.
- **Verification:**
  - Unit tests with fake registry.
  - Worker script test/mocked HTTP call.
  - Manual `workflow_dispatch` after deployment.

### T3.6 Digest email service and job

**Status:** pending

- **Owner:** agent.
- **Human setup:** H4.
- **PR size:** backend PR plus frontend copy if needed.
- **Build:**
  - Resend-backed `MailService` behind interface.
  - Plain text + simple HTML digest templates.
  - `POST /internal/jobs/send-digests`.
  - Mark included notifications with `email_sent_at`.
  - Thin `backend/workers/send_digests.py`.
  - `.github/workflows/digest.yml` with `workflow_dispatch`; add `schedule` only when production is ready.
- **Verification:**
  - Unit tests for no-unread suppression, email-disabled suppression, rendered template contents, marking sent.
  - Sandbox/live send smoke once H4 is complete.

---

## 9. Phase 4 — settings, currency, account lifecycle

### T4.1 FX rates and display currency

**Status:** pending

- **Owner:** agent.
- **PR size:** single full-stack PR.
- **Build:**
  - Frankfurter primary and `exchangerate.host` fallback.
  - 24h cache in `fx_rates_cache`.
  - `GET /api/fx/rates`.
  - Header currency switcher for CAD/USD/EUR/GBP.
  - Frontend conversion display only; CAD remains canonical for all stored values and thresholds.
- **Verification:**
  - Backend tests for cache hit/miss/provider failure.
  - Frontend tests for display conversion and CAD fallback.

### T4.2 Settings page

**Status:** pending

- **Owner:** agent.
- **PR size:** frontend-heavy full-stack PR.
- **Build:**
  - Display currency.
  - Global notifications on/off.
  - Default threshold.
  - Email digest on/off.
  - Light/dark theme toggle.
  - Revisit prompt toggles and `revisit_stale_days`.
  - Delete-account entry point with confirmation UI.
- **Verification:**
  - Backend profile validation tests.
  - Frontend tests for settings persistence and theme class.

### T4.3 Delete account

**Status:** pending

- **Owner:** agent with human confirmation before destructive live test.
- **PR size:** focused backend/frontend PR if not completed in T4.2.
- **Build:**
  - `DELETE /api/account`.
  - Delete user's products/listings/history/notifications/profile in one transaction or ordered cascade.
  - Call Supabase Auth admin API to delete auth user.
  - Frontend confirmation flow.
- **Verification:**
  - Backend tests with mocked Supabase admin client.
  - Manual live test only with a disposable test user and explicit human confirmation.

---

## 10. Phase 5 — retailer expansion and drift detection

Start after M3 proves the one-retailer architecture.

### T5.1 Benchmark harness

**Status:** pending

- **Owner:** agent.
- **PR size:** backend tooling PR.
- **Build:**
  - CLI/script to run representative URLs through structured data, `curl_cffi` + parser, and Playwright where installed.
  - Record success/failure by title, price, stock, image, variants, runtime, retries, blocked markers.
  - Output recommended strategy/fallback order per retailer.
- **Verification:**
  - Fixture-mode benchmark tests.
  - Document command and output format.

### T5.2 Easy Shopify/scrape-friendly retailers

**Status:** pending

- **Owner:** parallel agents, one PR per 1-3 retailers if fixtures and tests are independent.
- **Retailers:** `palmisleskate`, `dimemtl`, `tikiroomskate`, `eatyourwater`, then `indigo`.
- **Build:** scraper module, registry entry, fixtures, tests.
- **Verification:** fixture-only tests for each retailer.

### T5.3 Moderate retailers

**Status:** pending

- **Owner:** parallel agents, one retailer per PR unless two share identical implementation.
- **Retailers:** `apple_ca`, `canadiantire`, `costco_ca`, `abercrombie`, `oakley`, `vans_ca`.
- **Build:** benchmark first, then scraper/fixtures/tests.
- **Verification:** fixture tests and one controlled live/record pass per retailer when needed.

### T5.4 Bot-protected retailers

**Status:** pending

- **Owner:** focused agents, one retailer per PR.
- **Retailers:** `sportchek`, `footlocker_ca`, `nike_ca`, `amazon_ca`.
- **Build:** benchmark-driven strategy, minimal Playwright fallback only if measured.
- **Special rule:** `amazon_ca` must verify first-party "Sold by Amazon.ca" / "Ships from and sold by Amazon.ca"; reject otherwise.
- **Verification:** fixtures, benchmark notes, controlled live/record pass.

### T5.5 Drift detection workflow

**Status:** pending

- **Owner:** agent.
- **Human setup:** GitHub issue permissions/secrets if needed.
- **PR size:** tooling/workflow PR.
- **Build:**
  - `.github/workflows/retailer-drift.yml` weekly.
  - Local `make check-retailer-drift`.
  - Compare canonical live scrape to stored snapshots.
  - Open/update GitHub issue tagged `retailer-drift`.
- **Verification:**
  - Local mocked drift test.
  - `workflow_dispatch` dry run.

---

## 11. Phase 6 — deployment and production validation

### T6.1 Deployment docs and config hardening

**Status:** pending

- **Owner:** agent.
- **Human setup:** H5.
- **PR size:** docs/config PR.
- **Build:**
  - Update `docs/DEPLOYMENT.md` with final env vars: Gemini, Resend, worker token, app URL, scraper mode.
  - Confirm Render build/start commands, Playwright install notes if needed.
  - Confirm Vercel env setup.
  - Document Supabase redirect URLs.
- **Verification:** docs review and deployed health check.

### T6.2 Production smoke

**Status:** pending

- **Owner:** agent with human coordination.
- **Human setup:** H1-H5 complete.
- **PR size:** usually no code PR unless smoke uncovers bugs.
- **Verify:**
  - Google sign-in on deployed frontend.
  - Add one real Best Buy Canada URL.
  - Product appears with current price and category within 10 seconds.
  - Manual refresh works or returns a clear failure.
  - Internal scrape workflow dispatch succeeds.
  - Digest workflow dispatch sends or correctly suppresses email.
  - Account-delete flow verified on disposable test user only with confirmation.

### T6.3 Enable schedules

**Status:** pending

- **Owner:** agent with explicit human confirmation.
- **PR size:** workflow PR if schedules were deferred.
- **Build:**
  - Enable scrape cron `0 8 * * *` UTC.
  - Enable digest cron `0 14 * * *` UTC.
- **Verification:**
  - First scheduled run completes.
  - No duplicate price history from advisory lock.
  - No email when zero unread notifications.

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

**Status:** pending

- **Owner:** agent.
- **PR size:** frontend PR.
- **Build:**
  - Skeletons instead of spinners.
  - Optimistic feedback within 100ms for mutations.
  - Calm microcopy with no default exclamation marks.
  - Color-coded chips always include text.
  - Responsive layouts for mobile web.
- **Verification:**
  - Frontend tests.
  - axe checks where available.

### T7.2 Lighthouse gate

**Status:** pending

- **Owner:** agent.
- **PR size:** optimization PR(s) if needed.
- **Verify:**
  - Dashboard and product detail hit Lighthouse Performance >= 95 and Accessibility >= 95 on desktop throttled run.
  - Document command/results in PR.

### T7.3 V1 success-criteria checklist

**Status:** pending

- **Owner:** agent.
- **PR size:** docs PR.
- **Build:**
  - Add a final checklist mapping `docs/PRD.md` §15 criteria to implemented verification artifacts.
  - Link tests, workflows, manual smoke notes, and known limitations.
- **Verification:** checklist review.

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
| Deployment | M4 | Render/Vercel/GitHub Actions docs and smoke | Workflow scheduling until explicit enablement |

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

If starting from the current scaffold, run the first agents in this order:

1. T1.1 Core database schema and RLS.
2. T1.2 Backend settings, clients, and auth dependency.
3. T1.3 Frontend app shell and shared dependencies.
4. T1.4 Scraper contract and fixture mode harness.
5. T1.5 Service interfaces.
6. ~~T2.2 Generic JSON-LD/OG scraper and T2.3 `bestbuy_ca` fixture-backed scraper in parallel.~~ **Done** (T2.2 + T2.3).
7. T2.1 Auth and profile bootstrap once H1/H2 are ready enough.
8. T2.4 Categorization service.
9. T2.5 Product API vertical slice.
10. T2.6 Product frontend vertical slice.
11. T2.7 Local e2e one-retailer slice.
12. T2.8 Controlled live Best Buy validation.

Do not prioritize broad retailer expansion before step 12. A reliable app with one retailer is the intended MVP spine.
