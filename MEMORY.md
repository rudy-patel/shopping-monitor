# Project Memory

Chronological timeline of completed work, files changed, and known bugs/solutions. Agents: read this before making changes; reference via @MEMORY.md.

---

## [2026-06-14] T5.5 Drift detection (local tooling)

**What:** Shipped local-only retailer drift tooling (no GitHub Actions workflow — not run on CI/merge). Added `backend/scrapers/drift/` with live URL catalog, structural fingerprint normalization, committed baselines under `snapshots/`, compare/runner modules, optional GitHub issue sync (`--file-issues`), `scripts/check_retailer_drift.py`, `scripts/update_drift_snapshots.py`, `make check-retailer-drift` (live) and `make update-drift-snapshots` (fixtures).

**Locked behavior:** Compares structural fingerprint (field presence, variant shape, extraction path) — not price/title/stock values. One GitHub issue per retailer when `--file-issues`; auto-close on pass. `blocked` vs `shape_mismatch` vs `error` statuses. CI runs snapshot sync test only (no live network). Field expectations reuse benchmark catalog entries for the same slug/scenario. Fingerprint excludes scraper-mode `source`; `bestbuy_ca` canonicalizes `jsonld`/`bestbuy_api` → `bestbuy`.

**Live verification (2026-06-15):** `SCRAPER_MODE=live make check-retailer-drift` — **8/8 ok**; ~6s; no bot blocks from local run.

**Verification:** `ruff check .`, `pytest -m "not integration"` (547 passed), mocked drift tests; snapshot sync test; live run above. PR https://github.com/rudy-patel/shopping-monitor/pull/44

---

## [2026-06-14] T5.4 Bot-protected retailers (amazon_ca, nike_ca)

**What:** Shipped T5.4 bot-protected retailers in one PR: shared `scrapers/bot_protected_retailer.py` HTTP-only factory (no production Playwright), `amazon_ca` parser with first-party seller verification and twister variants, `nike_ca` `__NEXT_DATA__` parser with color/size variants, live-recorded fixtures (+6 HTML files), benchmark catalog entries, retailer labels, and extended `record_retailer_fixtures.py` (Amazon 1P validation, refined challenge markers).

**Locked behavior:** `amazon_ca` rejects third-party seller listings with `ScrapeBlockedError` on add and refresh; allows unavailable pages without a visible third-party seller. Production scrapers use `curl_cffi` only — Playwright not added to Render. Nike stock = any size `status==ACTIVE`.

**Fixture URLs recorded:** amazon — Echo Dot Charcoal (`B09B8V1LZ3` in_stock), Amazon Basics HDMI (`B014I8SSD0` multi_variant), Echo Dot OOS fixture derived from in_stock availability patch; nike — AF1 `CW2288-111` (in_stock/multi_variant), OOS fixture derived from inactive sizes.

**Deferred:** `sportchek`, `footlocker_ca` — live HTTP returned bot shell pages without title/price (Akamai/JS); Playwright excluded from V1 production by policy.

**Files:** `backend/scrapers/bot_protected_retailer.py`, `backend/scrapers/amazon_ca.py`, `backend/scrapers/nike_ca.py`, `backend/scrapers/extraction/amazon.py`, `backend/scrapers/extraction/nike.py`, `backend/scrapers/bootstrap.py`, `backend/scrapers/benchmark/catalog.yaml`, `backend/scrapers/benchmark/parsers.py`, `backend/scrapers/benchmark/recommend.py`, `backend/test/fixtures/retailers/amazon_ca/*`, `backend/test/fixtures/retailers/nike_ca/*`, `backend/test/test_bot_protected_retailer.py`, `backend/test/test_amazon_extraction.py`, `backend/test/test_amazon_ca_scraper.py`, `backend/test/test_nike_extraction.py`, `backend/test/test_nike_ca_scraper.py`, `backend/test/test_benchmark_harness.py`, `backend/test/test_fixture_convention.py`, `scripts/record_retailer_fixtures.py`, `frontend/src/lib/format.ts`, `backend/services/digest_templates.py`, `backend/scrapers/README.md`, `docs/ROADMAP.md`, `docs/PRD.md`, `MEMORY.md`.

**Verification:** `ruff check .`, `pytest -m "not integration"` (524 passed), `make benchmark-retailers`, `npm run lint`, `npm run test:run` with `SCRAPER_MODE=fixtures`.

**Review pass:** tightened Amazon 1P validation (availability-scoped OOS skip, marketplace anchor sellers, unverified buyable reject); DRY twister JSON helper; README/AGENTS sync.

---

## [2026-06-14] T6.2 Production smoke

**What:** Completed production smoke against Render + Vercel + Supabase. Live add/refresh/delete on production API for two retailers (`bestbuy_ca`, `palmisleskate`); digest `workflow_dispatch` suppression path; disposable account-delete smoke; Google OAuth UI + redirect verified; added `frontend/vercel.json` SPA rewrite so direct `/login` deep links return 200.

**Verified:**
- **Google sign-in:** Login page shows **Continue with Google** only (no dev login); OAuth redirect to `accounts.google.com` with Supabase callback + `redirect_to` production origin. Owner manual sign-in previously confirmed.
- **Live add (Render):** `bestbuy_ca` Switch 2 — 2.567s, title/62999 CAD/tech (`category_source=llm`); `palmisleskate` Bones Reds — 4.516s, title/2800 CAD/other (`category_source=heuristic`).
- **Refresh:** HTTP 200 for both products.
- **Digest:** Actions [run #27513581095](https://github.com/rudy-patel/shopping-monitor/actions/runs/27513581095) — `mail_provider: resend`, `users_emailed: 0`, `users_skipped_no_unread: 2`, `users_skipped_noop: 0`.
- **Account delete:** `smoke_delete_account.py --live --confirm` — ok.
- **Scrape (pre-verified):** [run #27509008501](https://github.com/rudy-patel/shopping-monitor/actions/runs/27509008501).
- **Cleanup:** All `smoke-t62-*` disposable users and smoke products removed.

**Files:** `backend/scripts/smoke_production_t6_2.py`, `backend/scripts/production_smoke_helpers.py`, `backend/test/test_production_smoke_helpers.py`, `frontend/vercel.json`, `frontend/src/test/vercel-config.test.ts`, `docs/ROADMAP.md`, `docs/DEPLOYMENT.md`, `docs/PRD.md`, `README.md`, `AGENTS.md`, `MEMORY.md`.

**Deferred:** Cron schedules → T6.3; 7-day reliability → T6.4; health probe `PGRST205` hardening optional.

---

## [2026-06-14] T5.3 Moderate retailers (indigo, apple_ca, abercrombie)

**What:** Shipped T5.3 moderate retailers in a single PR: `indigo` (Shopify + ProductGroup physical-format stock), `apple_ca` (buy-flow JSON-LD + config grid variants), `abercrombie` (embedded `productPrices` + scoped `primarySizeArray` SKU inventory). Shared `scrapers/structured_retailer.py` factory; parsers in `scrapers/extraction/{indigo,apple,abercrombie,embedded_json}.py`. Live-recorded fixtures, pytest per retailer, benchmark catalog (+9 entries), retailer labels, `scripts/record_retailer_fixtures.py`.

**Deferred from original T5.3 scope:** `costco_ca`, `oakley`, `canadiantire`, `vans_ca` (bot protection / low ROI).

**Locked behavior:** `default_strategy=STRUCTURED_DATA`, no Playwright fallbacks. Non-CAD rejected. Indigo OOS uses first physical ProductGroup variant (eBook may remain in stock). Abercrombie stock from scoped primary-product SKUs only (not sitewide recommendation widgets). Fixture post-processing applied for abercrombie in_stock SKU availability and apple_ca out_of_stock JSON-LD `OutOfStock`.

**Fixture URLs recorded:** indigo — the-will-of-the-many (in_stock), here-one-moment-indigo-exclusive-edition (multi_variant), dune (out_of_stock); apple_ca — buy-iphone/iphone-16 (in_stock/multi_variant), 6.1-inch-display-128gb-black config (out_of_stock); abercrombie — essential-popover-hoodie-61980823 (in_stock/multi_variant), heritage-heavyweight-popover-hoodie-62788916 (out_of_stock).

**Files:** `backend/scrapers/structured_retailer.py`, `backend/scrapers/{indigo,apple_ca,abercrombie}.py`, `backend/scrapers/extraction/{embedded_json,indigo,apple,abercrombie}.py`, `scripts/record_retailer_fixtures.py`, `backend/test/fixtures/retailers/{indigo,apple_ca,abercrombie}/*`, `backend/test/test_{indigo,apple_ca,abercrombie}_scraper.py`, `backend/test/test_structured_extraction.py`, `backend/scrapers/benchmark/catalog.yaml`, `docs/benchmarks/fixtures-2026-06-14.json`, `backend/scrapers/bootstrap.py`, `backend/services/factory.py`, labels in `digest_templates.py` + `frontend/src/lib/format.ts`.

**Verification:** `ruff check .`, `pytest -m "not integration"` (491 passed), `npm run lint`, `npm run test:run` (94 passed), `make benchmark-retailers` with `SCRAPER_MODE=fixtures`.

---

## [2026-06-14] T5.2 Shopify retailers (palmisleskate, tikiroomskate)

**What:** Shipped T5.2 easy Shopify retailers: shared `scrapers/shopify.py` factory and `scrapers/extraction/shopify.py` meta variant parser (JSON-LD/OG + `var meta` merge). Added `palmisleskate` (`palmisleskateshop.com`) and `tikiroomskate` with live-recorded fixtures, pytest coverage, benchmark catalog entries, retailer labels, and `scripts/record_shopify_fixtures.py`. Removed `dimemtl` (T3.1 enabler); discovery tests now use palmisle/tikiroom fixtures and `discovery_d` for cap tests.

**Locked behavior:** `default_strategy=STRUCTURED_DATA`, no fallbacks. Non-CAD listings rejected. Variant matrix from Shopify theme meta when JSON-LD omits `hasVariant`. `eatyourwater` and `indigo` deferred per product decision.

**Fixture URLs recorded:** palmisle — bones-reds-bearings (in_stock), violet-american-rapture-tee (multi_variant), creature-team-messenger-vx-deck (out_of_stock); tikiroom — bones-reds-bearings (in_stock), stussy-beach-ombre-plaid-shirt (multi_variant), colonialism-medicine-wheel-wheels (out_of_stock).

**Files:** `backend/scrapers/shopify.py`, `backend/scrapers/extraction/shopify.py`, `backend/scrapers/palmisleskate.py`, `backend/scrapers/tikiroomskate.py`, `scripts/record_shopify_fixtures.py`, `backend/test/fixtures/retailers/palmisleskate/*`, `backend/test/fixtures/retailers/tikiroomskate/*`, `backend/test/test_shopify_extraction.py`, `backend/test/test_palmisleskate_scraper.py`, `backend/test/test_tikiroomskate_scraper.py`, `backend/scrapers/benchmark/catalog.yaml`, `docs/benchmarks/fixtures-2026-06-14.json`, removed `dimemtl` module/fixtures/tests.

**Verification:** `ruff check .`, `pytest -m "not integration"` (470 passed), `npm run lint`, `npm run test:run` (94 passed), `make benchmark-retailers` with `SCRAPER_MODE=fixtures`.

**Deferred:** `eatyourwater` post-MVP; `indigo` → T5.3.

---

## [2026-06-14] T4.3 Delete account

**What:** Shipped `DELETE /api/account` using Supabase Auth admin `delete_user` with DB cascades for app data. Settings delete flow with `DeleteAccountDialog` confirmation. Post-delete: `signOut()` + navigate to `/login`. Returns 403 when `AUTH_BYPASS_ENABLED=true` or identity is on the protected deny list (`backend/core/protected_accounts.py`).

**Locked behavior:** Single `AlertDialog` confirm (no type-to-confirm). No new migrations. Integration/smoke use disposable `delete-account-<uuid>@shopping-monitor-test.invalid` users only. E2e excludes account delete (auth bypass would 403). Production verification deferred to T6.2.

**Files:** `backend/core/protected_accounts.py`, `backend/services/account_service.py`, `backend/routers/account.py`, `backend/main.py`, `backend/test/disposable_users.py`, `backend/test/test_protected_accounts.py`, `backend/test/test_account_router.py`, `backend/test/test_account_delete_integration.py`, `backend/test/fake_supabase.py`, `backend/scripts/smoke_delete_account.py`, `frontend/src/lib/account.ts`, `frontend/src/hooks/useDeleteAccount.ts`, `frontend/src/components/settings/DeleteAccountDialog.tsx`, `frontend/src/pages/SettingsPage.tsx`, `frontend/src/test/settings-page.test.tsx`, `backend/services/README.md`, `docs/AUTHENTICATION.md`, `docs/PRD.md`, `docs/ROADMAP.md`, `README.md`, `MEMORY.md`.

**Verification:** `ruff check .`, `pytest -m "not integration"` (460 passed), `npm run lint`, `npm run test:run` (94 passed), `npm run build`; integration test passed against local Supabase.

**Deferred:** Production disposable-user delete smoke → T6.2.

---

## [2026-06-14] T5.1 Scraper benchmark harness

**What:** Added fixture-mode benchmark harness (PRD §7.9): `scrapers/benchmark/` module with YAML catalog (`generic`, `bestbuy_ca`, `dimemtl`), three strategy runners (`structured_data`, `http_parse` with Best Buy JSON API sub-probe, optional `playwright`), recommendation engine, CLI `scripts/run_scraper_benchmark.py`, `make benchmark-retailers`, and committed `docs/benchmarks/fixtures-2026-06-14.json`. Added `PyYAML` to backend requirements; optional Playwright in `requirements-benchmark.txt`.

**Locked behavior:** No `--url` override; no production `scrape()` or registry default changes. `http_parse` skipped in fixture CI; live runs use `scraper_fetch` + retailer API probes. Recommendations advisory until human confirms `registry_snippet` before T5.2+.

**Fixture catalog notes:** `dimemtl` fixtures lack image URL and variant matrix — catalog `expect.image`/`variants` set false accordingly.

**Files:** `backend/scrapers/benchmark/*`, `scripts/run_scraper_benchmark.py`, `backend/requirements-benchmark.txt`, `backend/requirements.txt`, `backend/test/test_benchmark_harness.py`, `docs/benchmarks/`, `backend/scrapers/README.md`, `AGENTS.md`, `Makefile`, `docs/ROADMAP.md`, `MEMORY.md`.

**Verification:** `ruff check .`, `pytest -m "not integration"` (448 passed), `make benchmark-retailers` with `SCRAPER_MODE=fixtures`. PR https://github.com/rudy-patel/shopping-monitor/pull/38

**Second-pass cleanup:** Simplified catalog API (`slugs` filter only), cleaner skipped-strategy field output, fixed `_status_from_fields` to use `failed` not `blocked` for parse misses, accurate dimemtl catalog `expect` flags, docs sync (PRD §7.9, README, ROADMAP M5/T5.1/§15).

**Human follow-up:** Review `docs/benchmarks/fixtures-2026-06-14.json` `summaries` before T5.2 scrapers copy `registry_snippet` values.

---

## [2026-06-14] T4.2 Settings page

**What:** Full `/settings` UI for display currency, dark mode, notifications, default threshold, email digest, and revisit prompts. Removed header/mobile currency switcher (settings is sole control). Extended `ThemeContext` with profile hydrate + optimistic PATCH (mirrors `CurrencyContext`). Reordered providers: `QueryClientProvider → AuthProvider → ThemeProvider → CurrencyProvider`. Delete account section visible but gated (`ACCOUNT_DELETE_ENABLED = false`) until T4.3.

**Locked behavior:** Optimistic per-control PATCH with rollback toast on error. Profile wins over localStorage for theme/currency after login. `email_digest_enabled` and `notifications_enabled` remain independent. Revisit child controls disabled when master off. No `DELETE /api/account` in this PR.

**Files:** `frontend/src/pages/SettingsPage.tsx`, `frontend/src/contexts/ThemeContext.tsx`, `frontend/src/main.tsx`, `frontend/src/components/layout/TopNav.tsx`, `frontend/src/components/ui/switch.tsx`, `frontend/src/test/settings-page.test.tsx`, `frontend/src/test/theme.test.tsx`, `frontend/src/test/top-nav.test.tsx`, `frontend/src/test/routes.test.tsx`, `frontend/src/test/test-utils.tsx`, `frontend/e2e/settings.spec.ts`, `docs/ROADMAP.md`, `backend/services/README.md`, `MEMORY.md`.

**Verification:** `npm run lint`, `npm run test:run`, `npm run build`, `make test-e2e` with `SCRAPER_MODE=fixtures`. PRD updated: currency control lives in `/settings` only (U-CUR-2).

**Deferred:** Account deletion → T4.3; `scrape_failing` hide toggle not in scope.

---

## [2026-06-14] Docs status audit (T3.6 + T6.1 cross-reference)

**What:** Audited `main` against README, PRD, and ROADMAP after T3.6 (#35) and T6.1 (#34) merges. Fixed stale plan markers: ROADMAP §15 still said Phase 3 complete through T3.5 only; T3.6 verification and T6.1 build bullets still referenced H4/T3.6 as deferred; historical bootstrap list omitted T3.5/T3.6/T6.1; PRD §4.1 still listed "remaining notification workflows" and §10.3 digest runner lacked the T3.6 `workflow_dispatch`-only note (matching scrape). README was already current.

**Second pass (code review):** Added `users_skipped_noop` to digest job result for noop-provider observability (users with qualifying unread rows when `RESEND_API_KEY` unset), lazy mail-service init, `send_digests_completed` structured log, multi-user digest test, and smoke script `effective_app_base_url` for production link parity.

**Files:** `docs/ROADMAP.md`, `docs/PRD.md`, `docs/DEPLOYMENT.md`, `backend/services/digest_job_service.py`, `backend/services/README.md`, `backend/scripts/smoke_resend_digest.py`, `backend/test/test_digest_job_service.py`, `backend/test/test_internal_jobs_router.py`, `MEMORY.md`.

---

## [2026-06-14] T3.6 Digest email service and job

**What:** Implemented Resend-backed digest delivery: `ResendMailService`, `digest_templates.py` (copy mirrors `NotificationRow.tsx`), `digest_job_service.run_send_digests()`, `POST /internal/jobs/send-digests`, `backend/workers/send_digests.py`, `.github/workflows/digest.yml` (`workflow_dispatch` only), and `scripts/smoke_resend_digest.py` (dry-run default). Added pytest Resend guard in `conftest.py` (mirrors Gemini). `DigestEmail.to_email` now uses `EmailStr`.

**Locked behavior:** Select unread notifications with `email_sent_at IS NULL` within 90-day window. Skip when `email_digest_enabled=false` or zero qualifying rows. `notifications_enabled` does not gate digest. Mark `email_sent_at` only after successful Resend send; `RESEND_API_KEY` unset → `mail_provider: noop` with no sends or marks. Recipient resolved via Supabase Auth admin API. Revisit types deep-link to `/notifications`; `needs_input` → `/products/:id/variants`.

**Files:** `backend/services/resend_mail.py`, `backend/services/digest_templates.py`, `backend/services/digest_job_service.py`, `backend/services/mail.py`, `backend/services/factory.py`, `backend/core/settings.py`, `backend/routers/internal_jobs.py`, `backend/workers/send_digests.py`, `.github/workflows/digest.yml`, `backend/scripts/smoke_resend_digest.py`, `backend/test/test_digest_templates.py`, `backend/test/test_digest_job_service.py`, `backend/test/test_resend_mail.py`, `backend/test/test_workers_send_digests.py`, `backend/test/test_conftest_resend_guard.py`, `backend/test/conftest.py`, `backend/test/fake_supabase.py`, `backend/test/test_internal_jobs_router.py`, `backend/requirements.txt`, `backend/.env.example`, `backend/services/README.md`, `docs/DEPLOYMENT.md`, `docs/ROADMAP.md`, `MEMORY.md`.

**Verification:** `ruff check .`, `pytest -m "not integration"` (428 passed) with `SCRAPER_MODE=fixtures`. PR https://github.com/rudy-patel/shopping-monitor/pull/35. H4 done; sandbox live smoke recipient `rutvik@ualberta.ca` (human inbox check after one `--live` send).

**Deferred:** Digest cron schedule → T6.3; production `RESEND_API_KEY` on Render → post-merge (T6.2).

---

## [2026-06-14] T6.1 Deployment docs and config hardening

**What:** Rewrote `docs/DEPLOYMENT.md` with confirmed production URLs, env-var matrix, Supabase redirects, scrape workflow + deploy-wait docs, and verification checklist. Synced `backend/.env.example`; added `test_env_example_documents_settings_keys` to keep example aligned with `Settings`. Updated `docs/ROADMAP.md`, `docs/PRD.md` (§10.3/§10.8 — defer to DEPLOYMENT.md, scrape dispatch verified), `AGENTS.md`, and `README.md`.

**Production reference:** Frontend `https://shopping-monitor-nine.vercel.app`, backend `https://shopping-monitor-api.onrender.com`.

**Verified:** Scrape `workflow_dispatch` [run #27509008501](https://github.com/rudy-patel/shopping-monitor/actions/runs/27509008501) — `status: completed`, `listings_total: 13`, `duration_seconds: 57.9`. Prior runs failed on deploy-wait timeout before PR #32.

**Verification:** `make test` (396 backend + 80 frontend unit tests). PR https://github.com/rudy-patel/shopping-monitor/pull/34

**Deferred:** H4/Resend empty until T3.6; health probe `PGRST205` hardening → optional T6.2; cron schedules → T6.3.

**Files:** `docs/DEPLOYMENT.md`, `docs/ROADMAP.md`, `docs/PRD.md`, `backend/.env.example`, `backend/test/test_settings.py`, `AGENTS.md`, `README.md`, `MEMORY.md`.

---

## [2026-06-14] Roadmap status sync and H5 complete

**What:** Synced implementation status across agent docs: added missing PR links (T3.1 #25, T3.2 #26, T4.1 #29), marked M4 in progress with done/remaining breakdown, refreshed ROADMAP §15 next-task order, and updated human-setup checkpoints — **H5 done** (Render, Vercel, Supabase redirects, GitHub Actions `BACKEND_BASE_URL` + `WORKER_TOKEN`); **H4 pending** (Resend). T3.5 marked ready to start; T3.6 notes H4 blocks live digest smoke only.

**Files:** `docs/ROADMAP.md`, `docs/PRD.md`, `README.md`, `MEMORY.md`.

---

## [2026-06-14] T3.5 Internal scrape job endpoint

**What:** Implemented scheduled scrape-all: migration advisory-lock RPC helpers, `scrape_job_service.run_scrape_all()` with listing retry/backoff, `persist_listing_scrape_result()` extraction, evaluator mode split (`scrape_triggered` / `revisit_only` / `full`), `POST /internal/jobs/scrape-all` worker-token route, `backend/workers/scrape_all.py`, and `.github/workflows/scrape.yml` (`workflow_dispatch` only).

**Locked behavior:** Listing scope = all listings on products with `status IN ('active','needs_input')` including rejected rows. Lock contention → HTTP 200 `status=skipped`, `reason=lock_not_acquired`. Retry 3 attempts with sleep `2**attempt` (1s, 2s). Step 6 evaluators only for products touched this run; step 7 revisit-only per distinct user with active products. Scrape-all writes `price_history.source='scheduled'` and does **not** touch `last_refresh_at` / `last_user_interaction_at`. Manual refresh unchanged (`mode=full`, `source=manual`).

**Files:** `backend/db/migrations/002_scrape_job_advisory_lock.sql`, `backend/services/scrape_job_service.py`, `backend/services/product_service.py`, `backend/services/notification_evaluation.py`, `backend/routers/internal_jobs.py`, `backend/workers/scrape_all.py`, `.github/workflows/scrape.yml`, `backend/test/test_scrape_job_service.py`, `backend/test/test_internal_jobs_router.py`, `backend/test/test_workers_scrape_all.py`, `backend/test/test_migration_002_scrape_job_advisory_lock.py`, `backend/test/test_notification_evaluation_service.py`, `backend/test/fake_supabase.py`, `docs/DATABASE.md`, `docs/DEPLOYMENT.md`, `docs/ROADMAP.md`, `backend/services/README.md`, `AGENTS.md`, `MEMORY.md`.

**Verification:** `ruff check .`, `python scripts/check_migrations.py`, `pytest -m "not integration"` (395 passed) with `SCRAPER_MODE=fixtures`. PR https://github.com/rudy-patel/shopping-monitor/pull/31. Migrations applied on production; scrape `workflow_dispatch` verified [run #27509008501](https://github.com/rudy-patel/shopping-monitor/actions/runs/27509008501) (documented in T6.1).

**Deferred:** Cron schedule → T6.3; digest job → T3.6.

---

## [2026-06-14] T4.1 FX rates and display currency

**What:** Implemented live FX with Frankfurter primary + ExchangeRate-API Open Access fallback, 24h `fx_rates_cache` via `CachedFxService`, authenticated `GET /api/fx/rates`, header currency switcher synced to `profiles.display_currency` (hydrate on login, PATCH on change with rollback toast), and display-only conversion via `useFormatPriceCents` with silent CAD fallback when rates fail.

**Locked behavior:** Stored prices/thresholds/trends remain CAD; provider failure serves stale cache (200 + `stale: true`) or 503 when empty; frontend never surfaces FX errors; profile wins over localStorage after login.

**Files:** `backend/services/fx_providers.py`, `backend/services/fx_cache_service.py`, `backend/services/factory.py`, `backend/routers/fx.py`, `backend/main.py`, `backend/core/settings.py`, `backend/test/test_fx_cache_service.py`, `backend/test/test_fx_router.py`, `backend/test/fake_supabase.py`, `frontend/src/lib/fx.ts`, `frontend/src/hooks/useFxRates.ts`, `frontend/src/hooks/useFormatPriceCents.ts`, `frontend/src/contexts/CurrencyContext.tsx`, `frontend/src/lib/format.ts`, product/notification display components, `frontend/src/test/format-price.test.tsx`, `frontend/src/test/top-nav.test.tsx`, `docs/PRD.md`, `docs/ROADMAP.md`, `backend/services/README.md`, `MEMORY.md`.

**Verification:** `ruff check .`, `pytest -m "not integration"` (369 passed), `npm run lint`, `npm run test:run` (80 passed), `npm run build` with `SCRAPER_MODE=fixtures`. PR https://github.com/rudy-patel/shopping-monitor/pull/29

**Deferred:** Settings page currency control → T4.2.

## [2026-06-14] T3.4 Notification evaluators and post-scrape orchestration

**What:** Implemented all five notification evaluator bodies with typed `NotificationEvaluationContext`, pricing helpers (`baseline_max_daily_minimum`, `current_daily_minimum`), shared `pricing_data.load_price_observations`, orchestrator (`notification_evaluation.py`), and wiring into `refresh_product()` (listing snapshots, failure-count reset on success, post-scrape evaluation). Exported `run_post_scrape_evaluation` and `run_revisit_evaluation_for_active_products` for T3.5.

**Locked behavior:** Manual refresh increments `scrape_failure_count` on failure but `scrape_failing` only fires for `scrape_source="scheduled"`. Profile `notifications_enabled=false` suppresses all evaluator-backed notifications. `scrape_failing` fires once at count=3 (no repeat at 4+; re-fires after success reset→3). Revisit evaluators run on manual refresh. Price-drop payload uses `old_price_cents` / `new_price_cents`.

**Files:** `backend/services/pricing.py`, `backend/services/pricing_data.py`, `backend/services/notifications.py`, `backend/services/notification_evaluation.py`, `backend/services/product_service.py`, `backend/test/test_notification_evaluators.py`, `backend/test/test_revisit_90_day_fixture.py`, `backend/test/test_notification_evaluation_service.py`, `backend/test/test_services_pricing.py`, `backend/test/test_services_notifications.py`, `backend/test/test_products_router.py`, `backend/services/README.md`, `docs/ROADMAP.md`, `MEMORY.md`.

**Verification:** `ruff check .`, `pytest -m "not integration"` (356 passed) with `SCRAPER_MODE=fixtures`. PR https://github.com/rudy-patel/shopping-monitor/pull/28

**Deferred:** Scheduled scrape-all caller → T3.5; digest email → T3.6.

## [2026-06-14] T3.3 Notification API and in-app bell

**What:** Implemented the notification read API and frontend bell: `notification_service.py` with 90-day query filter, offset/limit pagination, mark-read (per-id and all) with `last_user_interaction_at` touch, revisit keep/archive actions (archive via `update_product`), three authenticated routes, `FakeSupabaseClient` extensions (`order`, `gte`, `range`), notifications page with load-more and click-to-navigate mark-read, TopNav unread badge (refetch on window focus only), and Vitest coverage for page actions and bell badge.

**Locked behavior:** Non-revisit rows mark-read on click before navigate; revisit types use Keep/Archive buttons only; bell count is global within 90-day window, not page-local.

**Files:** `backend/services/notification_service.py`, `backend/routers/notifications.py`, `backend/main.py`, `backend/test/fake_supabase.py`, `backend/test/test_notifications_router.py`, `frontend/src/lib/notifications.ts`, `frontend/src/hooks/useNotifications.ts`, `frontend/src/components/notifications/NotificationRow.tsx`, `frontend/src/pages/NotificationsPage.tsx`, `frontend/src/components/layout/TopNav.tsx`, `frontend/src/test/notifications-page.test.tsx`, `frontend/src/test/top-nav.test.tsx`, `frontend/src/test/routes.test.tsx`, `backend/services/README.md`, `docs/ROADMAP.md`, `MEMORY.md`.

**Verification:** `ruff check .`, `pytest -m "not integration"` (318 passed), `npm run lint`, `npm run test:run`, `npm run build` with `SCRAPER_MODE=fixtures`. PR https://github.com/rudy-patel/shopping-monitor/pull/27

**Deferred:** Notification producers (price_drop, revisit triggers) → T3.4; digest email → T3.6; 90-day purge job → future.

## [2026-06-14] T3.2 Listing review API and UI

**What:** Implemented listing review endpoints (`accept`, `reject`, `delete`), cap-counting helper (`count_cap_listings`; rejected rows no longer block discovery), truncated `discovery_justification` persisted in `scrape_snapshot`, review display fields on listing API responses, product detail Needs Review queue (Accept / Reject / Open source), main listings table with match confidence and Remove for non-primary `auto_added`/`accepted` rows, rejected and needs-review rows hidden from main table.

**Locked behavior:** Rejected listings hidden everywhere in UI; accept does not re-check cap; short LLM justification shown as review reason with "Possible match" fallback; discovery cap uses cap-counting statuses (rejected frees a slot).

**Files:** `backend/services/discovery.py`, `backend/services/product_service.py`, `backend/routers/products.py`, `backend/test/test_discovery.py`, `backend/test/test_products_router.py`, `frontend/src/lib/products.ts`, `frontend/src/hooks/useProducts.ts`, `frontend/src/components/products/NeedsReviewQueue.tsx`, `frontend/src/components/products/ListingRow.tsx`, `frontend/src/pages/ProductDetailPage.tsx`, `frontend/src/test/listing-review.test.tsx`, `frontend/src/test/product-detail.test.tsx`, `frontend/src/test/product-fixtures.ts`, `docs/ROADMAP.md`, `MEMORY.md`.

**Verification:** Backend and frontend unit tests with `SCRAPER_MODE=fixtures`. PR https://github.com/rudy-patel/shopping-monitor/pull/26

**Deferred:** Notifications bell → T3.3; Playwright e2e for review flow; backfill of `discovery_justification` on existing rows.

## [2026-06-14] T3.1 Cross-retailer discovery engine

**What:** Implemented the cross-retailer discovery engine: `services.matching` confidence scoring (renormalized weights without pHash), `services.discovery` background orchestrator with auto-add/needs-review/discard caps, `GeminiFlashLlmProvider.discover()` with Google Search grounding and structured JSON, `gemini_discover_timeout_s` setting, H3 smoke script `scripts/smoke_gemini_discover.py`, frontend conditional polling (detail 3s / list 5s) with list-cache invalidation on discovery complete, and embedded `dimemtl` Shopify fixture scraper for two-retailer fixture validation.

**Locked behavior:** `discovery_complete` notification only when ≥1 listing auto-added or queued; discovery runs immediately for `needs_input` products with empty variants; first candidate per retailer slug; early stop at 4 non-primary auto-adds (no further needs-review).

**Files:** `backend/services/matching.py`, `backend/services/discovery.py`, `backend/services/gemini.py`, `backend/services/factory.py`, `backend/core/settings.py`, `backend/routers/products.py`, `backend/scrapers/dimemtl.py`, `backend/scrapers/bootstrap.py`, `backend/scripts/smoke_gemini_discover.py`, `backend/test/test_matching.py`, `backend/test/test_discovery.py`, `backend/test/test_dimemtl_scraper.py`, `backend/test/discovery_test_retailers.py`, `backend/test/test_services_gemini.py`, `backend/test/test_products_router.py`, `backend/test/fixtures/retailers/discovery_*`, `backend/test/fixtures/retailers/dimemtl/*`, `frontend/src/hooks/useProducts.ts`, `frontend/src/components/products/DiscoveryIndicator.tsx`, `frontend/src/test/product-polling.test.ts`, `backend/services/README.md`, `docs/ROADMAP.md`, `MEMORY.md`.

**Removed:** `backend/services/discovery_stub.py`.

**Verification:** `ruff check .`, `pytest -m "not integration"` (288 passed), `npm run lint`, `npm run test:run` with `SCRAPER_MODE=fixtures`. PR https://github.com/rudy-patel/shopping-monitor/pull/25

**Deferred:** Notifications bell → T3.3; image pHash → future.

## [2026-06-14] T2.8 Controlled live Best Buy validation

**What:** Completed controlled live validation for Nintendo Switch 2 Console (`https://www.bestbuy.ca/en-ca/product/nintendo-switch-2-console/19296507`). Tier A/B/C all pass with live scrape, live Gemini categorization, and full UI add flow. HTML PDP requests returned Akamai **403 Access Denied** from the agent environment (curl_cffi and Playwright); live scrape succeeded via Best Buy JSON product API fallback (`/api/v2/json/product/{sku}` → `ScrapeSource.HTTP_PARSE`). Recorded `switch_2_in_stock` fixture (JSON-LD HTML synthesized from API + raw `.json` snapshot).

**Validation results (2026-06-14, `GEMINI_API_KEY` configured):**

| Tier | Result | Notes |
| --- | --- | --- |
| A (scraper) | pass | title *Nintendo Switch 2 Console*, price **62999** CAD cents, in stock, brand Nintendo, source `http_parse` |
| B (API) | pass | `POST /api/products` 201, listing `scrape_status=ok`, `category=tech`, **`category_source=llm`** |
| C (UI) | pass | Dev login → Add Product with live URL → detail shows title/$629.99/stock/Best Buy/Tech → dashboard lists product; API confirms `category_source=llm` |

**Files:** `backend/scrapers/bestbuy_ca.py`, `backend/scrapers/extraction/bestbuy_api.py`, `scripts/record_bestbuy_fixtures.py`, `backend/test/fixtures/retailers/bestbuy_ca/switch_2_in_stock.html`, `backend/test/fixtures/retailers/bestbuy_ca/switch_2_in_stock.json`, `backend/test/test_bestbuy_ca_scraper.py`, `backend/test/test_bestbuy_api_extraction.py`, `backend/scrapers/README.md`, `docs/ROADMAP.md`, `MEMORY.md`.

**Deferred:** Playwright HTML fallback if JSON API is ever blocked.

## [2026-06-14] T2.7 Local e2e vertical slice

**What:** Completed the first local vertical slice end-to-end test: expanded Playwright spec to cover add → detail assertions → category/threshold edits → single refresh → dashboard → archive → history → restore → UI delete. Playwright `webServer` auto-starts backend (fixture mode + auth bypass) and frontend; added GitHub Actions `playwright-e2e` job with Supabase secrets. Fixed TanStack Query list-cache helpers that were applying array updaters to detail query caches (blocked PATCH mutations in browser). Dev auth now restores across reload when Supabase is configured. Closed M2 milestone.

**Files:** `frontend/e2e/products.spec.ts`, `frontend/e2e/helpers/auth.ts`, `frontend/playwright.config.ts`, `frontend/src/lib/products.ts`, `frontend/src/hooks/useProducts.ts`, `frontend/src/contexts/AuthContext.tsx`, `frontend/src/test/auth-context.test.tsx`, `frontend/src/test/products-query-keys.test.ts`, `.github/workflows/ci.yml`, `Makefile`, `docs/ROADMAP.md`, `README.md`, `AGENTS.md`, `MEMORY.md`.

**Verification:** `make setup-integration-env && make test-integration && make test && make test-e2e` with `SCRAPER_MODE=fixtures` and `AUTH_BYPASS_ENABLED=true`.

**Deferred:** Live Best Buy validation → T2.8; Google OAuth e2e variant out of scope for T2.7.

## [2026-06-13] T2.6 Product frontend vertical slice

**What:** Implemented the product frontend vertical slice: Add Product modal (URL + category), monochrome dashboard grouped by category, filtered flat list, product detail (listings table, threshold/category PATCH, refresh, archive, delete), variant picker for `needs_input`, **archived products History page with restore**, TanStack Query hooks with optimistic PATCH/archive/restore, Vitest coverage, Playwright scaffold with archive→history→restore e2e, and optional frontend live API integration test (`VITE_INTEGRATION=1`). Backend micro-amendments: `available_variants` on listing responses, `needs_review_count` on product summaries.

**Files:** `backend/routers/products.py`, `backend/services/product_service.py`, `backend/test/test_products_router.py`, `frontend/src/lib/products.ts`, `frontend/src/lib/categories.ts`, `frontend/src/lib/format.ts`, `frontend/src/hooks/useProducts.ts`, `frontend/src/components/products/*`, `frontend/src/components/ui/select.tsx`, `frontend/src/components/ui/badge.tsx`, `frontend/src/components/ui/alert-dialog.tsx`, `frontend/src/components/add-product/AddProductDialog.tsx`, `frontend/src/pages/DashboardPage.tsx`, `frontend/src/pages/ListPage.tsx`, `frontend/src/pages/ProductDetailPage.tsx`, `frontend/src/pages/VariantPickerPage.tsx`, `frontend/src/index.css`, `frontend/src/test/*.test.tsx`, `frontend/src/test/integration/products-api.integration.test.ts`, `frontend/e2e/products.spec.ts`, `frontend/playwright.config.ts`, `frontend/package.json`, `Makefile`, `AGENTS.md`, `docs/ROADMAP.md`, `MEMORY.md`.

**Deferred:** Listing accept/reject → T3.2; FX conversion display → T4.1.

**Review pass:** Fixed ProductCard invalid button-inside-link markup (archive kebab actions), context-aware archived detail back-link, list-cache rollback helper, retailer labels in list filters; ROADMAP T2.6/T2.7 wording aligned to shipped history/restore.

## [2026-06-13] T2.5 Product API vertical slice

**What:** Implemented the backend Product API vertical slice: seven authenticated endpoints (`POST/GET/PATCH/DELETE /api/products`, refresh, select-variant), product/listing orchestration with fixture-backed scraping and categorization, product-level trend/best-price helpers, discovery stub via BackgroundTasks (`discovery_status='complete'`), and first `price_history` row with `source='scheduled'` on add (no `last_refresh_at` on add). Extended scraper registry `lookup_by_url()` to resolve `fixtures.local/<retailer_slug>/<scenario>` URLs for tests and local dev.

**Files:** `backend/routers/products.py`, `backend/services/product_service.py`, `backend/services/discovery_stub.py`, `backend/main.py`, `backend/scrapers/registry.py`, `backend/test/fake_supabase.py`, `backend/test/__init__.py`, `backend/test/test_products_router.py`, `backend/test/test_products_integration.py`, `backend/test/test_profile_router.py`, `backend/test/test_scraper_registry.py`, `docs/ROADMAP.md`, `MEMORY.md`.

**Gotchas:** Integration inserts require auth-bypass dev user `00000000-0000-0000-0000-000000000001` in Supabase Auth (FK on `products.user_id`). Unit tests must re-register scrapers after registry-resetting scraper tests — `test_products_router.py` fixture calls `register_generic()` / `register_bestbuy_ca()`. Generic `ScrapeBlockedError` on add still creates a product with `scrape_status='blocked'` and no price history.

**Deferred:** Listing accept/reject/delete → T3.2; notification evaluators on refresh → T3.4; real discovery → T3.1; frontend product UI → T2.6.

## [2026-06-13] Integration env placeholder guard

**What:** Fixed integration tests failing opaquely against `your-project-id.supabase.co`. Added `backend/integration_env.py` placeholder detection; `setup_integration_env.py` now rejects example values instead of writing them; integration pytest helpers share the same validation; `REQUIRE_INTEGRATION_ENV=1` surfaces setup-script failure at collection time.

**Files:** `backend/integration_env.py`, `backend/test/integration_env.py`, `backend/test/test_integration_env.py`, `scripts/setup_integration_env.py`, `backend/test/conftest.py`, `backend/test/test_rls_smoke.py`, `backend/test/test_products_integration.py`, `AGENTS.md`, `MEMORY.md`.

## [2026-06-13] T2.4 Gemini live-call guardrails

**What:** Blocked live Gemini in pytest/CI: autouse `conftest` fixture clears `GEMINI_API_KEY` and mocks `genai.Client`; CI asserts empty key; smoke script defaults to dry-run heuristic path and requires `--live` for real API calls; regression test proves pytest passes with a key in the shell env.

**Files:** `backend/test/conftest.py`, `backend/test/test_conftest_gemini_guard.py`, `backend/scripts/smoke_gemini_categorize.py`, `.github/workflows/ci.yml`, `backend/services/README.md`, `AGENTS.md`, `MEMORY.md`.

## [2026-06-13] T2.4 categorization service

**What:** Implemented `GeminiFlashLlmProvider` with structured JSON categorization, 1.5s thread-pool timeout, quota/error mapping, and `get_categorizer()`/`get_llm_provider()` factory wiring. Reordered heuristic precedence to retailer default → breadcrumbs → title/brand (PRD §7.7). Added `google-genai==2.8.0`, Gemini settings (`GEMINI_MODEL`, `GEMINI_CATEGORIZE_TIMEOUT_S`), human smoke script `scripts/smoke_gemini_categorize.py`, and mocked unit tests.

**Files:** `backend/services/gemini.py`, `backend/services/factory.py`, `backend/services/categorizer.py`, `backend/services/__init__.py`, `backend/core/settings.py`, `backend/scripts/smoke_gemini_categorize.py`, `backend/test/test_services_gemini.py`, `backend/test/test_services_categorizer.py`, `backend/test/test_settings.py`, `backend/requirements.txt`, `backend/services/README.md`, `AGENTS.md`, `docs/ROADMAP.md`, `MEMORY.md`.

**Deferred:** Product API wiring + `category_source` persistence → T2.5; frontend Add modal category dropdown → T2.6; `LlmProvider.discover()` Gemini implementation → T3.1.

## [2026-06-13] T2.3 bestbuy_ca fixture-backed scraper

**What:** Added the `bestbuy_ca` retailer scraper with real recorded HTML fixtures (`in_stock`, `out_of_stock`, `multi_variant`), JSON-LD/OG extraction enriched by Best Buy embedded state (`window.__INITIAL_STATE__`) for stock and colour variants, `curl_cffi` primary transport with `httpx` fallback in `scraper_fetch()`, bootstrap registration, and fixture-only pytest coverage.

**Fixture source URLs (for T5.5 drift checks):**
- in_stock: https://www.bestbuy.ca/en-ca/product/lenovo-yoga-slim-7x-14-5-touchscreen-copilot-pc-laptop-cosmic-blue-snapdragon-x-elite-16gb-ram-1tb-ssd/19220080
- out_of_stock: https://www.bestbuy.ca/en-ca/product/nintendo-switch-oled-model-super-mario-bros-wonder-bundle-with-3-month-online-individual-membership/19180065
- switch_2_in_stock: https://www.bestbuy.ca/en-ca/product/nintendo-switch-2-console/19296507 (T2.8; JSON-LD HTML synthesized from product API when PDP blocked)

**Files:** `backend/scrapers/bestbuy_ca.py`, `backend/scrapers/extraction/bestbuy.py`, `backend/scrapers/http.py`, `backend/scrapers/bootstrap.py`, `backend/scrapers/extraction/jsonld.py`, `backend/scrapers/mode.py`, `backend/main.py`, `backend/requirements.txt`, `backend/test/fixtures/retailers/bestbuy_ca/*.html`, `backend/test/test_bestbuy_ca_scraper.py`, `backend/test/test_scraper_http_guard.py`, `backend/test/test_scraper_registry.py`, `backend/test/conftest.py`, `scripts/record_bestbuy_fixtures.py`, `backend/scrapers/README.md`, `docs/ROADMAP.md`, `MEMORY.md`.

**Deferred:** Product API wiring → T2.5; Playwright HTML fallback if JSON API is blocked → future retailer work; JSON product API fallback shipped in T2.8 when PDP HTML is Akamai-blocked.

## [2026-06-13] T2.2 generic JSON-LD/OG scraper

**What:** Implemented the `generic` retailer fallback: JSON-LD Product extraction first, OpenGraph/product meta fallback, CAD-only guard (`NotCanadianListingError`), no-price → `ScrapeBlockedError`, no-title → `ScrapeParseError`, fixture URL resolver (`fixtures.local/<slug>/<scenario>`), and fixture-only pytest coverage. Added `beautifulsoup4` for HTML parsing. Production registration via `scrapers.bootstrap` with idempotent `register_generic()` for test registry resets.

**Files:** `backend/scrapers/generic.py`, `backend/scrapers/bootstrap.py`, `backend/scrapers/structured_data.py`, `backend/scrapers/fixture_url.py`, `backend/scrapers/extraction/` (`types.py`, `jsonld.py`, `opengraph.py`, `price.py`), `backend/test/fixtures/retailers/generic/*.html`, `backend/test/test_generic_scraper.py`, `backend/test/conftest.py`, `backend/test/test_scraper_registry.py`, `backend/scrapers/exceptions.py`, `backend/scrapers/README.md`, `backend/requirements.txt`, `backend/pytest.ini`, `docs/ROADMAP.md`, `MEMORY.md`.

**Deferred:** Product API wiring for generic listings → T2.5; frontend "Generic scraper — may be unreliable" label → T2.6.

## [2026-06-14] T2.1 review pass

**What:** Second-pass cleanup: `update_profile` now catches PostgREST `PGRST116` (real Supabase behavior when PATCH hits a missing row) instead of checking `data is None`; extracted `_select_profile` / `_apply_profile_update` helpers; fake client update+single raises `PGRST116` to match production; deduped test profile fixture via exported `defaultProfileResponse`; `ProviderStack` accepts shared `QueryClient`; added test that `signOut` clears profile query cache; updated `docs/AUTHENTICATION.md` module table and OAuth note.

**Files:** `backend/services/profile_service.py`, `backend/test/test_profile_router.py`, `frontend/src/test/setup.ts`, `frontend/src/test/test-utils.tsx`, `frontend/src/test/profile-bootstrap.test.tsx`, `frontend/src/test/auth-context.test.tsx`, `docs/AUTHENTICATION.md`, `MEMORY.md`.

## [2026-06-14] T2.1 auth and profile bootstrap

**What:** Wired Google OAuth via Supabase on the login page; added GET /api/profile (idempotent upsert with PRD §8.1 defaults) and PATCH /api/profile (partial, range-validated update); added useProfile/useUpdateProfile hooks called from ProtectedRoute to bootstrap the profile on first authenticated render; signOut now clears the React Query cache so a re-login as another user starts clean.

**Files:** backend/services/profile_service.py, backend/routers/profile.py, backend/main.py, backend/test/test_profile_router.py, frontend/src/contexts/AuthContext.tsx, frontend/src/pages/LoginPage.tsx, frontend/src/lib/profile.ts, frontend/src/hooks/useProfile.ts, frontend/src/components/layout/ProtectedRoute.tsx, frontend/src/test/setup.ts, frontend/src/test/login-page.test.tsx, frontend/src/test/routes.test.tsx, frontend/src/test/auth-context.test.tsx, frontend/src/test/profile-bootstrap.test.tsx, frontend/src/test/App.test.tsx, docs/AUTHENTICATION.md, docs/ROADMAP.md, MEMORY.md.

**Deferred:** profile-backed theme/currency hydration → T4.1/T4.2; settings UI for editing profile fields → T4.2; account delete → T4.3; live Google OAuth smoke recorded in PR walkthrough.

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
