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
