# Shopping Monitor — Product Requirements (V1)

> **Status:** Draft v1.1 — revised technical direction for the first working prototype.
> **Owner:** Product (you). **Audience:** Engineering, AI agents implementing the prototype.
> **Last updated:** 2026-06-11.

---

## 1. Overview

**Shopping Monitor** is a personal-use web app that lets a user paste a product URL from a Canadian online store and have the app monitor its price (and stock) over time, automatically find the same product at up to four other retailers for side-by-side comparison, surface meaningful price drops and back-in-stock events in a daily summary, and organize everything into a tidy categorized shopping list.

The goal is to make the user **confident they are paying a fair price for things they want**, without having to manually check stores or scroll deal sites.

V1 is a free, low-traffic prototype optimized for a single primary user plus a handful of friends — not a public consumer product. We pay nothing for infrastructure, scraping, LLM, FX, or email in this phase.

---

## 2. Vision & Goals

### 2.1 Vision

A user pastes a URL for a thing they want. The app quietly takes care of the rest — finding the best price across retailers, watching for sales, telling them when something is worth buying — and presents a clean, organized "wishlist" of everything they're tracking.

### 2.2 V1 goals (in priority order)

1. **Reliable price tracking** for a curated set of Canadian retailers, plus best-effort tracking of any other pasted URL.
2. **Multi-retailer comparison** on add: surface up to 4 alternates for the same product when they exist.
3. **Honest sale signal**: a clear, color-coded indicator of whether a product's price has trended down, up, or stayed flat over the past 30 days, plus opt-in notifications when a price meaningfully drops.
4. **Tidy organization** of the user's shopping list into a small fixed set of categories.
5. **Frictionless sign-in** with Google so the user (and friends) can be onboarded in seconds.

### 2.3 Non-goals for V1 (explicit)

The following are deliberately **out of scope** for V1. They are documented in §13 so they aren't forgotten, but engineering should not build them in this phase.

- Shipping, tax, or duty calculation/estimation of any kind.
- A "price rating" that compares against MSRP or against prices at other retailers ("cheaper elsewhere"). V1 ships only a 30-day trend chip.
- Search-based product addition (catalogs/indexes). URL paste only.
- Browser extension, mobile app, push notifications, SMS notifications.
- Sharing or collaborative lists between users.
- Public registration / anti-abuse / terms of service / GDPR tooling beyond basic auth + delete-my-account.
- Periodic re-discovery of new retailers for an existing product (one-shot at add time only).
- AI auto-categorization (manual category selection with an LLM-friendly hook for V2).
- Variant "families" — one product entry equals one specific variant (size + color, etc.).
- Paid data sources (hosted scraping APIs, premium LLM APIs, exact landed-cost services).

---

## 3. Target Users

**Primary persona — "Patient shopper":**
A consumer in Canada who knows what they want, doesn't need it urgently, and would happily wait for a 20% sale. They currently bookmark items in 30 browser tabs and check them sporadically. They want to consolidate that habit into one tool.

**Secondary persona — "Curious friend":**
A friend of the primary user who signs in with Google to try the app on their own list of items. Same Canadian context, same usage pattern, but their data is fully private from the primary user.

There is **one product** in V1 — it serves both personas identically. There is no concept of admin, no concept of team, no concept of public profile.

---

## 4. V1 Scope Summary

| In scope | Out of scope |
|---|---|
| Google SSO sign-in via Supabase | Email/password, magic links, other SSO |
| Per-user private shopping list | Shared/collaborative lists |
| Add product by pasting URL | Search, browser extension, share-sheet |
| Variant inference from URL/page | Variant family grouping |
| "Needs input" flag when variant unclear | Auto-guessing variants |
| Daily scheduled price + stock scrape | Real-time / sub-daily monitoring |
| Manual "refresh now" button (1-hour cooldown per product) | Unlimited manual refresh |
| Agentic cross-retailer discovery, one-shot at add | Periodic re-discovery |
| Up to 5 listings per product (1 user-pasted + up to 4 discovered) | Unlimited listings per product |
| Auto-add high-confidence matches; queue medium-confidence for review | Auto-add everything |
| 30-day price trend chip (down / same / up) with color coding | Historical price chart, MSRP comparison, cross-retailer rating |
| Per-product notification threshold (default 20%, configurable) | Per-listing thresholds, smart predictions |
| Daily digest email + persistent in-app notification list | Per-event emails, push/SMS |
| Back-in-stock notifications (separate from price drops) | Real-time stock alerts |
| 5 fixed categories: Clothing / Shoes / Home / Tech / Other | Custom user categories, AI auto-categorization |
| Archive (instead of delete) on purchase, with a history view | Detailed purchase analytics |
| CAD as canonical currency; cosmetic display-currency switcher with free FX API | Multi-currency monitoring or thresholds |

---

## 5. User Stories

Each story below is a V1 commitment.

### 5.1 Authentication

- **U-AUTH-1.** As a new user, I can sign in with my Google account in one click and land on an empty dashboard.
- **U-AUTH-2.** As a returning user, I stay signed in across sessions until I sign out.
- **U-AUTH-3.** As a user, I can delete my account from settings, which erases my products, listings, price history, and notifications.

### 5.2 Adding products

- **U-ADD-1.** As a signed-in user, I can paste a product URL into a single input and submit it.
- **U-ADD-2.** When I submit a URL from a natively supported retailer, the app extracts the title, image, current price, stock state, and variant attributes (size, color) and immediately creates a tracked product.
- **U-ADD-3.** If the URL specifies a variant via path/query, that variant is selected automatically.
- **U-ADD-4.** If the page has multiple variants and the URL is ambiguous, the app flags the product as **"Needs input"** and shows me a variant picker on a follow-up step.
- **U-ADD-5.** If the URL is from a retailer **not** on our supported list, the app still creates a tracked product using a best-effort generic scraper, and labels the listing "Generic scraper — may be unreliable."
- **U-ADD-6.** Immediately after I add a product, the app kicks off background cross-retailer discovery. I see a "Looking for other retailers…" indicator on the product card.
- **U-ADD-7.** When discovery completes, high-confidence matches are added automatically, medium-confidence matches go into a **"Needs review"** list under the product, and I receive an in-app notification telling me discovery finished.

### 5.3 Viewing & organizing products

- **U-VIEW-1.** My default dashboard shows all active products grouped by the 5 fixed categories.
- **U-VIEW-2.** I can toggle to a flat list view and filter by category, retailer, or "has unreviewed matches."
- **U-VIEW-3.** Each product card shows: image, title, brand, retailer of best current price, best current price (in display currency), 30-day trend chip, alternate retailers count, last-refreshed timestamp, manual refresh button, and a kebab menu.
- **U-VIEW-4.** Clicking a card opens a product detail page showing every listing (one row per retailer) with its current price, stock state, last-refreshed timestamp, scrape status, and a link to the source URL.
- **U-VIEW-5.** I can manually re-categorize a product into a different fixed bucket from its detail page.
- **U-VIEW-6.** I can edit a product's notification threshold from its detail page (overriding my global default).
- **U-VIEW-7.** I can manually refresh a product (forces a fresh scrape of every listing) with a 1-hour per-product cooldown.

### 5.4 Cross-retailer comparison

- **U-CMP-1.** On a product detail page, listings are sorted by current price ascending so the cheapest is always on top.
- **U-CMP-2.** Each listing shows confidence score (for non-primary listings), retailer name, current price, stock state, and a "Remove this match" button.
- **U-CMP-3.** I can review the "Needs review" queue per product: each candidate shows the candidate URL's title, image, price, and reason for the medium confidence. I accept, reject, or open the URL for closer inspection.

### 5.5 Price trend & sale signal

- **U-TREND-1.** Every active product shows one of three chips:
  - **Green** "Down in the last 30 days"
  - **Neutral** "Same in the last 30 days" (also the default when we have less than 7 days of data)
  - **Red** "Up in the last 30 days"
- **U-TREND-2.** The trend is computed off the **best listing's** price history over a rolling 30-day window (see §7.4 for the exact rule).

### 5.6 Notifications

- **U-NOT-1.** When the best price for a product drops by ≥ the product's threshold (default 20%) relative to its rolling-30-day baseline, the user gets one notification (in-app + included in next day's email digest).
- **U-NOT-2.** When any listing transitions from out-of-stock to in-stock, the user gets a separate "Back in stock" notification.
- **U-NOT-3.** All notifications appear in a persistent in-app **Notifications** page (bell icon in header), with read/unread state, sorted newest-first, retained for 90 days.
- **U-NOT-4.** Once per day, the user receives an email digest summarizing all unread notifications since the previous digest. The digest is suppressed entirely if there are zero events.
- **U-NOT-5.** I can disable notifications globally or per product. I can edit my default threshold and per-product overrides in settings.

### 5.7 Currency display

- **U-CUR-1.** Prices are stored and computed in **CAD** always. All thresholds and trend math operate on the CAD value.
- **U-CUR-2.** The header has a display-currency switcher; default is CAD. Supported display currencies in V1: CAD, USD, EUR, GBP. (More can be added trivially.)
- **U-CUR-3.** Conversion uses a free FX API (see §10.5). Rates are cached for 24 hours. Conversion failures fall back silently to CAD display.

### 5.8 Archiving & purchase history

- **U-ARC-1.** I can archive a product from its detail page or card kebab menu (e.g., after buying it).
- **U-ARC-2.** Archived products move to a separate **History** view; they retain all stored price history and listings.
- **U-ARC-3.** I can restore an archived product to "active."
- **U-ARC-4.** I can permanently delete a product (irreversible).

### 5.9 Settings

- **U-SET-1.** Settings include: display currency, global default notification threshold %, daily email digest on/off, time zone (for digest scheduling), and "Delete my account."

---

## 6. Information Architecture

V1 frontend routes (all behind auth except `/login`):

| Route | Purpose |
|---|---|
| `/login` | Google SSO landing |
| `/` | Dashboard, default = grouped by category |
| `/list` | Flat list + filters |
| `/products/:id` | Product detail (listings, history, settings, needs-review queue) |
| `/products/:id/variants` | Variant picker for "Needs input" products |
| `/notifications` | Bell-icon page; full notification log |
| `/history` | Archived products |
| `/settings` | Global preferences + delete account |

A persistent top nav contains: app title/logo, "Add Product" CTA, currency switcher, bell icon (notifications), avatar menu (settings, sign out).

The "Add Product" CTA opens a modal with a single URL input. On submit, the modal closes and the user is taken to the new product detail page in a loading state.

---

## 7. Functional Requirements

### 7.1 Authentication

- Supabase Auth with Google as the **only** enabled provider.
- Frontend uses `@supabase/supabase-js` for client-side session.
- Backend validates the user's Supabase JWT on every API call using JWKS (see `docs/AUTHENTICATION.md`). `AUTH_BYPASS_ENABLED=true` is permitted in local dev only and uses a fixed dev user UUID.
- On first sign-in, a row is upserted into `profiles` with defaults (see §8.1).
- Delete-account flow: backend deletes all of the user's `products`, `product_listings`, `price_history`, `notifications`, and `profiles` rows in a single transaction, then calls Supabase Auth admin API to delete the auth user.

### 7.2 Product addition

**Adding flow (synchronous portion):**

1. Frontend POSTs `{ url }` to `POST /api/products`.
2. Backend identifies the retailer by matching `url` against the supported-retailer registry (see §11). If no match, falls back to the `generic` scraper.
3. Backend invokes the retailer's scraper to extract: `title`, `brand`, `image_url`, `current_price_cad`, `currency_seen`, `is_in_stock`, `available_variants` (list of `{attribute_name, attribute_value}`), `selected_variant` (if inferable from URL).
4. Backend creates one `products` row and one `product_listings` row (the user-pasted URL, marked `is_primary=true`).
5. If `selected_variant` is unambiguous → product status = `active`. If multiple variants and URL is ambiguous → product status = `needs_input`; the variant picker route loads `available_variants` from the listing's stored snapshot.
6. Backend records the first `price_history` snapshot.
7. Backend enqueues the cross-retailer discovery job (see §7.3) and returns the new product to the client. The client navigates to `/products/:id`.

**Currency on add:**
If the source page shows a non-CAD price (e.g., a US-only retailer URL), the scraper marks `currency_seen` and the listing is **rejected** with a friendly error to the user: "This product appears to be priced in USD. V1 only supports Canadian listings." This guards the user from accidentally tracking US store URLs.

### 7.3 Cross-retailer discovery (agentic)

Runs once, asynchronously, after a product is added.

**Inputs:** product title, brand, selected variant attributes, primary listing's price, image URL.

**Algorithm:**

1. Compose a prompt for the configured free LLM (current Gemini Flash free-tier model with Google Search grounding by default; see §10.7) asking it to find URLs of the *exact same variant* of this product at any of the natively supported retailers (§11), restricted to `.ca` domains or each retailer's Canadian region.
2. The LLM returns up to 8 candidate URLs with a one-line justification each.
3. For each candidate URL, backend runs the appropriate retailer scraper to extract `title`, `brand`, `variant_attributes`, `image_url`, `current_price_cad`, `is_in_stock`.
4. Backend computes a **confidence score** for each candidate using:
   - Title token Jaccard similarity vs. reference (weight 0.4)
   - Brand exact match (weight 0.2)
   - Variant attribute exact match across all attributes (weight 0.3)
   - Image perceptual-hash similarity (weight 0.1, optional in V1 — drop to 0 and renormalize weights if it adds complexity)
5. **Auto-add** candidates with score ≥ 0.85, up to a cap of 4 non-primary listings (5 total per product). **Queue** candidates with 0.6 ≤ score < 0.85 to the product's "Needs review" list. **Discard** the rest.
6. Stop scoring more candidates as soon as the auto-add cap is hit.
7. Mark the discovery job complete on the `products` row and write an in-app notification to the user.

**Failure handling:** if the LLM returns no candidates or the call fails, log a warning and complete the discovery job silently — the user keeps their single primary listing.

**Cost control:** discovery is one-shot per product (never re-runs automatically). The user can force a re-discovery by deleting and re-adding the product. This caps Gemini-free-tier spend at one call per product creation.

### 7.4 Price monitoring & trend

**Daily scrape job (GitHub Actions cron, ~04:00 America/Toronto):**

1. Fetch every active `product_listings` row.
2. For each, invoke the appropriate retailer scraper (or the generic scraper).
3. Persist a `price_history` row with the observed price, stock state, and timestamp.
4. Update the listing's `last_known_price_cents`, `is_in_stock`, `last_scraped_at`, and `scrape_status` columns.
5. Increment `scrape_failure_count` on failure; reset to 0 on success.
6. After all scrapes finish, evaluate notification triggers (§7.5).
7. Send daily digest emails to users with at least one new event since their last digest.

**Manual refresh:**
Endpoint `POST /api/products/:id/refresh`. Cooldown = last `refreshed_at` on product must be ≥ 1 hour ago. Runs the same scrape logic synchronously across the product's listings, returns updated state, evaluates notification triggers for that product only.

**Trend computation:** For each product, take the lowest in-stock price observed each day over the past 30 days from the product's best listing (whichever listing currently has the lowest price). Compute:

- `delta_pct = (price_today - price_30d_ago) / price_30d_ago`

If we have **< 7 days** of history: chip = **neutral / "Same in the last 30 days."**
Else if `delta_pct <= -0.03`: chip = **green / "Down in the last 30 days."**
Else if `delta_pct >= +0.03`: chip = **red / "Up in the last 30 days."**
Else: chip = **neutral / "Same in the last 30 days."**

(The ±3% deadband prevents flapping for trivial fluctuations.)

### 7.5 Notification triggers

Evaluated after every successful scrape (scheduled or manual).

**Price-drop trigger:**

- Let `baseline = MAX(price_history) over the trailing 30 days, restricted to in-stock observations` for the product's currently-best listing.
- Let `current = newest observed in-stock price` for that listing.
- If `(baseline - current) / baseline ≥ product.notification_threshold_pct / 100`, fire a `price_drop` notification.
- **Debounce:** suppress if a `price_drop` notification was already created for this product in the last 24 hours.

**Back-in-stock trigger:**

- Fire a `back_in_stock` notification when any listing's `is_in_stock` transitions from `false` to `true`.
- Debounce: suppress if a `back_in_stock` notification was already created for the same listing in the last 24 hours.

**Other notification types:**

- `discovery_complete` — written exactly once when cross-retailer discovery finishes.
- `needs_input` — written exactly once when a product is created in `needs_input` status.
- `scrape_failing` — written when a listing fails 3 consecutive scheduled scrapes; user can hide it from settings if noisy.

### 7.6 Email digest

- Sent at most once per day per user, at user-local 08:00 (default America/Toronto unless user changes time zone).
- Provider: **Resend** free tier (see §10.4). Pluggable behind a `MailService` interface so providers can swap.
- Template: plain text + simple HTML. Lists each event with product title, change summary, and a deep link back to the app.
- Skipped entirely if the user has zero unread notifications since the previous digest, or if they have email notifications disabled.

### 7.7 Categories

- Five fixed categories: `clothing`, `shoes`, `home`, `tech`, `other`.
- On product creation, backend assigns a category using **retailer breadcrumbs first, keyword heuristics second, `other` last** (e.g., a Foot Locker product gets `shoes` because Foot Locker is mapped to `shoes`; a Best Buy laptop gets `tech` via breadcrumb keywords; everything that can't be classified goes to `other`).
- Users can re-categorize manually at any time; this overrides the heuristic permanently.
- LLM auto-categorization is **out of V1** but the column accepts arbitrary values and the heuristic function is isolated so we can swap it for an LLM call later without schema changes.

### 7.8 Generic fallback scraper

For URLs from any unsupported retailer:

- Use the shared scraper pipeline (§10.6), starting with a lightweight browser-like HTTP request (`curl_cffi` preferred for TLS/browser impersonation; `httpx` acceptable only for sites that do not block it).
- Apply schema.org `Product` JSON-LD extraction first (most retailers expose this).
- Fall back to OpenGraph tags (`og:title`, `og:image`, `og:price:amount`, `og:price:currency`, `product:availability`).
- If neither yields a price, mark the listing `scrape_status='blocked'` and surface "Couldn't read price from this site" to the user; product stays in their list with manual refresh available.

The generic scraper never participates in cross-retailer discovery (it can't reliably normalize variants).

### 7.9 Scraper benchmark pipeline

Before implementing the full supported-retailer list, engineering must add a small benchmark harness that can run a candidate URL through multiple extraction strategies and record comparable results. The goal is to learn which approach works for each retailer before committing to a brittle scraper implementation.

**Benchmark inputs:**

- A curated fixture file of representative product URLs across the V1 retailers, including at least one easy Shopify-style store, one JSON-LD-friendly store, and one bot-protected store.
- Expected fields when known: title, price, stock state, image URL, selected variant, available variants.

**Strategies to compare:**

1. Embedded structured data only: schema.org JSON-LD, retailer-specific embedded JSON, and OpenGraph/product meta tags.
2. `curl_cffi` + parser: browser-like TLS/HTTP fingerprinting plus BeautifulSoup/lxml extraction.
3. Playwright: real browser rendering for sites that need JavaScript execution or stronger bot-evasion.

**Out of scope for the benchmark:** hosted scraping APIs such as Firecrawl. V1 must remain free to operate indefinitely, so paid or one-time-credit scraping vendors are excluded from the core plan.

**Benchmark output:**

- Per-strategy success/failure for title, price, stock, image, and variant fields.
- Runtime and retry count.
- Blocked/CAPTCHA/403/429 markers.
- Recommended default strategy per retailer and fallback order.

The retailer registry (§11) should store each retailer's selected default strategy and allowed fallbacks so the app can switch approaches without changing product/business logic.

---

## 8. Data Model

All new tables live in `public` with **RLS enabled** per `docs/DATABASE.md`. Migrations are added under `backend/db/migrations/` in numeric order. All timestamps are `TIMESTAMPTZ`. Prices are stored as integer cents in CAD; never floats.

### 8.1 `profiles`

| Column | Type | Notes |
|---|---|---|
| `user_id` | `uuid` PK | References `auth.users(id)` ON DELETE CASCADE |
| `display_currency` | `text` | Default `'CAD'`. Allowed: CAD, USD, EUR, GBP. |
| `default_threshold_pct` | `int` | Default `20`. Range 1–95. |
| `email_digest_enabled` | `bool` | Default `true`. |
| `digest_local_hour` | `int` | Default `8`. |
| `time_zone` | `text` | IANA tz, default `'America/Toronto'`. |
| `created_at`, `updated_at` | `timestamptz` | |

**RLS:** Pattern A — users select/update their own row.

### 8.2 `products`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `user_id` | `uuid` | FK to `auth.users`, indexed |
| `title` | `text` | |
| `brand` | `text` | nullable |
| `image_url` | `text` | nullable |
| `category` | `text` | enum-like; one of `clothing/shoes/home/tech/other` |
| `status` | `text` | `active`, `needs_input`, `archived` |
| `notification_threshold_pct` | `int` | nullable; falls back to `profiles.default_threshold_pct` |
| `notifications_enabled` | `bool` | Default `true`. |
| `discovery_status` | `text` | `pending`, `running`, `complete`, `failed` |
| `last_refresh_at` | `timestamptz` | nullable; used to enforce manual refresh cooldown |
| `created_at`, `updated_at` | `timestamptz` | |

**RLS:** Pattern A. Index on `(user_id, status)`.

### 8.3 `product_listings`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `product_id` | `uuid` | FK products, indexed |
| `retailer_slug` | `text` | e.g. `amazon_ca`, `nike_ca`, `generic` |
| `url` | `text` | the canonical product URL |
| `variant_attributes` | `jsonb` | e.g. `{"size":"10","color":"white"}` |
| `is_primary` | `bool` | true for the URL the user pasted |
| `match_confidence` | `numeric(4,3)` | nullable; only set for discovered listings |
| `review_status` | `text` | `auto_added`, `needs_review`, `accepted`, `rejected` |
| `last_known_price_cents` | `int` | nullable; CAD cents |
| `is_in_stock` | `bool` | nullable until first scrape |
| `last_scraped_at` | `timestamptz` | |
| `scrape_status` | `text` | `ok`, `failing`, `blocked` |
| `scrape_failure_count` | `int` | default 0 |
| `created_at`, `updated_at` | `timestamptz` | |

**RLS:** Pattern A via join on `products.user_id`.

### 8.4 `price_history`

| Column | Type | Notes |
|---|---|---|
| `id` | `bigserial` PK | |
| `listing_id` | `uuid` | FK product_listings, indexed |
| `price_cents` | `int` | CAD cents, NOT NULL |
| `is_in_stock` | `bool` | |
| `observed_at` | `timestamptz` | indexed |
| `source` | `text` | `scheduled`, `manual` |

**RLS:** Pattern A via join. Retain forever in V1 (volume is tiny — one row per listing per day, ~365 rows per listing per year).

### 8.5 `notifications`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `user_id` | `uuid` | FK auth.users |
| `product_id` | `uuid` | nullable |
| `listing_id` | `uuid` | nullable |
| `type` | `text` | `price_drop`, `back_in_stock`, `discovery_complete`, `needs_input`, `scrape_failing` |
| `payload` | `jsonb` | type-specific data (old price, new price, retailer, etc.) |
| `is_read` | `bool` | default false |
| `email_sent_at` | `timestamptz` | nullable; populated when included in a digest |
| `created_at` | `timestamptz` | indexed |

**RLS:** Pattern A.

### 8.6 `fx_rates_cache`

Backend-only table; Pattern B (service-role-only).

| Column | Type |
|---|---|
| `pair` | `text` PK (e.g. `'CAD_USD'`) |
| `rate` | `numeric` |
| `fetched_at` | `timestamptz` |

**Retailer config does not live in the DB** in V1 — it's a Python module so adding a retailer is a code change reviewed in PR (intentional; see §11).

---

## 9. API Surface

REST under `/api`, all behind auth (Supabase JWT).

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/products` | Add a new product from a URL |
| `GET` | `/api/products` | List user's products with filters (`status`, `category`) |
| `GET` | `/api/products/:id` | Product detail (includes listings + recent history) |
| `PATCH` | `/api/products/:id` | Update category, threshold, notifications-enabled, status (archive/restore) |
| `DELETE` | `/api/products/:id` | Hard delete |
| `POST` | `/api/products/:id/refresh` | Trigger manual refresh (enforces 1h cooldown) |
| `POST` | `/api/products/:id/select-variant` | Resolve `needs_input` by selecting a variant |
| `POST` | `/api/products/:id/listings/:listing_id/accept` | Accept a `needs_review` discovery candidate |
| `POST` | `/api/products/:id/listings/:listing_id/reject` | Reject one |
| `DELETE` | `/api/products/:id/listings/:listing_id` | Remove a non-primary listing |
| `GET` | `/api/notifications` | Paginated notification list |
| `POST` | `/api/notifications/mark-read` | Bulk mark-read |
| `GET` | `/api/profile` | Current user's settings |
| `PATCH` | `/api/profile` | Update settings |
| `DELETE` | `/api/account` | Delete account + all data |
| `GET` | `/api/fx/rates` | Convenience: current FX rates for supported display currencies |

Internal (service-role, called from GitHub Actions worker, not exposed to browser):

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/internal/jobs/scrape-all` | Daily worker entry point |
| `POST` | `/internal/jobs/send-digests` | Daily worker entry point |

Internal endpoints require a shared-secret header (`X-Worker-Token`).

---

## 10. Tech Stack & System Design

### 10.1 Frontend

- **React + Vite + TypeScript** (already scaffolded in `frontend/`).
- **State/data:** TanStack Query for server data; React Context for session & display currency.
- **UI library:** Tailwind CSS + shadcn/ui (or similar lightweight component kit). No heavy design system in V1.
- **Auth:** `@supabase/supabase-js` with Google OAuth.
- **Hosting:** Vercel free tier per `docs/DEPLOYMENT.md`.

### 10.2 Backend

- **FastAPI** (existing `backend/main.py`). Python 3.12.
- **Auth:** Supabase JWT validation via JWKS, per `docs/AUTHENTICATION.md`.
- **DB client:** `supabase-py` (service-role for backend writes; PostgREST-via-RLS optional).
- **Hosting:** Render free tier (web service). The free tier sleeps after 15 minutes idle; first request after sleep is slow. Acceptable for V1.

### 10.3 Background scraping

- **Runner:** GitHub Actions cron workflow under `.github/workflows/scrape.yml`, scheduled at `0 8 * * *` UTC (≈ 04:00 America/Toronto).
- **Action runs:** a Python entrypoint in `backend/workers/scrape_all.py` that calls `POST /internal/jobs/scrape-all` on the deployed backend (`X-Worker-Token` from `WORKER_TOKEN` secret). The backend does the actual scraping inline using its own scraper modules — this keeps scraper code in one place.
- **Repository visibility:** public GitHub repository is preferred if Actions minutes ever become a free-tier constraint. A private repository is acceptable while included free minutes comfortably cover once-daily jobs.
- **Headless browser for protected sites:** `playwright` in the backend, used only by retailers that need JavaScript execution or cannot be handled by structured data / `curl_cffi`. Render free tier can run Playwright (with installed deps in the build step), but cold starts and memory pressure make it a fallback, not the default.
- **Rationale for this split:** GitHub Actions provides free scheduling with visible workflow logs; the backend hosts the actual logic and DB credentials. This avoids duplicating scraping code between an Actions runner and the API.

### 10.4 Email

- **Provider:** Resend free tier (3,000 emails/month, 100/day). Requires a verified domain or use Resend's `onboarding@resend.dev` sandbox sender for V1 if no domain is wired up.
- **Sent by:** the daily digest worker (`POST /internal/jobs/send-digests`), triggered by a second GitHub Actions cron at `0 12 * * *` UTC (≈ 08:00 America/Toronto). For users in other time zones, the worker filters by `profiles.digest_local_hour` and `profiles.time_zone` and only sends to users whose local time matches.

### 10.5 FX rates

- **Provider:** `frankfurter.app` (free, no key, ECB rates). Primary.
- **Fallback:** `exchangerate.host` if Frankfurter fails.
- Backend fetches and caches in `fx_rates_cache` for 24 hours.
- Frontend never calls FX providers directly — always via `GET /api/fx/rates`.

### 10.6 Scraping implementation strategy

V1 should optimize for a free, maintainable, Python-native scraping stack rather than relying on hosted scraping vendors.

**Default extraction pipeline, in order:**

1. **Structured data / retailer JSON:** parse schema.org JSON-LD, embedded app state JSON, retailer APIs discovered from product pages, and OpenGraph/product meta tags.
2. **Browser-like HTTP:** use `curl_cffi` with current Chrome/Safari impersonation, realistic headers, cookies/session reuse where useful, and BeautifulSoup/lxml/selectolax-style parsing.
3. **Playwright fallback:** render with a real browser only when the benchmark harness proves the retailer requires JavaScript execution or stronger browser behavior.

**Explicit V1 exclusion:** Firecrawl and similar hosted scraping APIs are not part of the V1 operating plan. They may be useful for manual research outside the product, but the production app must not depend on one-time credits or paid scraping vendors.

**Design contract:** scraper modules expose the same `scrape(url) -> ProductSnapshot` interface regardless of strategy. Product, notification, and UI code should not know whether a listing was scraped through structured data, `curl_cffi`, or Playwright.

### 10.7 LLM (cross-retailer discovery)

- **Provider:** Google Gemini API, using the current Flash-family model available on the free tier at implementation time, with Google Search as a grounding tool when available.
- **Free-tier guardrails:** discovery is one-shot per product, the prompt is bounded in size, and we cap candidates at 8. If the free-tier quota is exceeded, discovery is skipped silently and a notification is recorded ("Cross-retailer discovery temporarily unavailable").
- **Pluggable interface:** a `DiscoveryProvider` abstraction so we can swap LLMs later without rewriting the discovery pipeline.

### 10.8 Secrets & environment

Add to `backend/.env.example`:

```
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
AUTH_BYPASS_ENABLED=true

GEMINI_API_KEY=
RESEND_API_KEY=
WORKER_TOKEN=          # shared secret for /internal/jobs/* endpoints
APP_BASE_URL=          # used in email links
```

`frontend/.env.example` is unchanged from the scaffold.

GitHub Actions secrets needed: `WORKER_TOKEN`, `BACKEND_BASE_URL`.

---

## 11. Supported Retailers (V1)

Each natively supported retailer needs a scraper module exposing a `scrape(url) -> ProductSnapshot` function and metadata describing its default extraction strategy and fallback order.

| Slug | Domain(s) | Default category | Notes |
|---|---|---|---|
| `amazon_ca` | amazon.ca | other | Strict 1P only — must verify "Sold by Amazon.ca" or "Ships from and sold by Amazon.ca" in scraper. Benchmark first; likely needs `curl_cffi` or Playwright fallback. |
| `bestbuy_ca` | bestbuy.ca | tech | Cloudflare-protected; benchmark structured data / `curl_cffi` before Playwright. |
| `apple_ca` | apple.com/ca | tech | JSON endpoints often available without a browser. |
| `nike_ca` | nike.com/ca | shoes | Aggressive bot protection; benchmark `curl_cffi`; Playwright may be needed. |
| `sportchek` | sportchek.ca | clothing | Akamai-protected; benchmark before selecting default strategy. |
| `indigo` | indigo.ca | other | Generally scrape-friendly. |
| `canadiantire` | canadiantire.ca | home | Region-aware (asks for store); use the central/online price. |
| `costco_ca` | costco.ca | other | Some pages behind member login — we restrict to public listings only. |
| `abercrombie` | abercrombie.com (Canada region) | clothing | |
| `oakley` | oakley.com/en-ca | other | |
| `footlocker_ca` | footlocker.ca | shoes | |
| `vans_ca` | vans.ca | shoes | |
| `palmisleskate` | palmisle.com | other | Small Shopify store; easy. |
| `dimemtl` | dimemtl.com | clothing | Small Shopify store; easy. |
| `tikiroomskate` | tikiroomskateboards.com | other | Small Shopify store; easy. |
| `eatyourwater` | eatyourwater.com | clothing | Small Shopify store; easy. |
| `generic` | (any other domain) | `other` | Best-effort structured data / OG with lightweight HTTP only; no Playwright. |

**Per-retailer scraper checklist (engineering contract):** title, brand (best-effort), image URL, current price in CAD cents, in-stock boolean, list of available variant attribute combinations, and the selected variant attributes for the input URL (when inferable from URL or page state).

**Engineering note on scraper reliability:** several of the above retailers run aggressive bot protection. Do not assume Playwright is required until the benchmark harness proves it; try structured data and `curl_cffi` first, then use Playwright as the measured fallback. Expect periodic breakage when sites change. V1 accepts this brittleness as a known limitation; see §13.

---

## 12. Non-Functional Requirements

- **Performance:** product list page loads in < 2s with up to 200 products. Manual refresh of one product should complete in < 30s for non-Playwright retailers; Playwright-backed retailers may be slower because browser cold start dominates.
- **Reliability:** daily scrape job retries each listing up to 2 times with exponential backoff. A run is considered successful if at least 80% of listings scrape successfully.
- **Cost:** $0/month for V1. All providers used in the core product (Supabase, Vercel, Render, GitHub Actions, Gemini, Resend, Frankfurter) have free tiers that should accommodate a personal user plus a few friends with once-daily scraping. The core plan excludes hosted scraping APIs such as Firecrawl because one-time credits or paid monthly quotas are incompatible with indefinite free operation.
- **Security:**
  - RLS on every `public` table.
  - Service-role key never reaches the frontend.
  - Internal `/internal/jobs/*` endpoints require `X-Worker-Token`.
  - All outbound user-facing links in emails go to the deployed app, not to retailers directly (to avoid affiliate-link-injection accusations).
- **Privacy:** Account-delete erases all user data; aggregated price history for shared listings is also deleted in V1 (we don't yet have a cross-user shared catalog).
- **Observability:** structured logs from backend (stdout JSON), GitHub Actions workflow logs for the cron worker. No paid telemetry in V1.
- **Accessibility:** the frontend must pass basic axe-core checks (semantic landmarks, keyboard nav, color contrast). Color-coded chips use both color and text (never color alone).
- **Browser support:** Chrome, Safari, Firefox latest two majors. Mobile web responsive but no native app.

---

## 13. Risks & Known Limitations

| Risk / limitation | Impact | V1 mitigation |
|---|---|---|
| Scrapers break when retailer HTML changes | Listings stop refreshing | `scrape_failing` notification after 3 consecutive failures; structured logs; per-retailer scraper is a small isolated module |
| Bot-protected retailers (Nike, Amazon, Best Buy) block server IPs | Some listings refresh inconsistently | Benchmark structured data, `curl_cffi`, and Playwright per retailer; accept best-effort, mark failures clearly to user |
| Gemini free tier rate-limited or quota exhausted | Discovery silently fails | Pluggable provider interface; skip + notify user; one-shot per product caps usage |
| Gemini model names / free-tier limits change | Implementation docs become stale | Select the current Flash-family free-tier model at implementation time and keep discovery behind `DiscoveryProvider` |
| Render free tier cold-starts (15-min idle sleep) | First post-idle request is slow (~30s) | Acceptable for V1; daily worker stays warm during its run; manual refresh users see a spinner |
| Single-region (Canada) hardcoded assumption | Non-Canadian friend can't really use it | V1 explicitly Canada-only; document in onboarding |
| Variant inference is fragile across diverse retailer URL patterns | Users will see "Needs input" more often than ideal | Explicit "Needs input" UX; not a crash |
| Currency switcher could mislead user if FX rates are stale | User sees a price they can't actually pay in that currency | 24h cache is acceptable for cosmetic display; thresholds are always CAD |
| Amazon 1P-only rule is hard to verify programmatically | Could accidentally track a 3P seller | Scraper requires literal "Sold by Amazon.ca" string; otherwise reject with friendly error |
| Email digest could land in spam | User misses sale alerts | In-app notifications are the source of truth; email is convenience layer |
| GitHub Actions cron is best-effort (can run late) | Daily scrape may shift by minutes | Acceptable; not a correctness issue |
| GitHub Actions free minutes differ by repository visibility | Private repo could eventually consume included minutes | Prefer public repo if Actions minutes become a constraint; daily V1 jobs are low-volume |
| ToS / scraping ethics | Long-term legal exposure if app grows | V1 is personal-use; revisit before any public launch |

---

## 14. Out of Scope / Future Work (V2 candidates)

Captured here so they aren't lost.

- **Cross-retailer "cheaper elsewhere" indicator** (requires reliable matching at scale).
- **AI auto-categorization** (LLM call swappable behind the existing category heuristic).
- **MSRP-based pricing context** ("This is at MSRP" / "This is below MSRP").
- **Real-time / sub-daily monitoring** for selected high-priority products.
- **Periodic re-discovery** of new retailers for existing products.
- **Browser extension** for one-click add from any product page.
- **Push / SMS notifications**.
- **Mobile app** (PWA at minimum).
- **Multi-country support** (region-aware scrapers, regional FX defaults, ship-to filtering).
- **Shipping, tax, and duty estimation** for true landed cost.
- **Shared / collaborative lists** between users.
- **Public product catalog** with affiliate revenue.
- **Smart target-price suggestions** based on historical seasonality.
- **Wishlist sharing** (export, public page).

---

## 15. Success Criteria for V1

V1 is considered complete when:

1. A user can sign in with Google, paste a URL from any of the 16 supported retailers (or any other site), and have it appear in their list within 10 seconds with a current price.
2. The scraper benchmark harness has been run against representative URLs for every supported retailer and records the selected default strategy plus fallback order.
3. The daily scrape runs on schedule for 7 consecutive days with ≥ 80% per-listing success rate across the user's products.
4. Cross-retailer discovery finds at least one additional listing for at least 60% of products that exist at multiple supported retailers (acknowledging some products genuinely only exist at one).
5. A user receives a daily digest email containing accurate price-drop and back-in-stock events when those events occur.
6. The 30-day trend chip is visibly correct for products with ≥ 7 days of data.
7. The display-currency switcher correctly converts and renders for CAD/USD/EUR/GBP.
8. A user can archive, restore, delete, and re-categorize products.
9. A user can delete their account and verify (via Supabase dashboard) that their data is gone.

---

## 16. Open Questions (deferred — to revisit before V2)

These are deliberate trade-offs in V1, written down so the next planning round can revisit them with usage data:

- Should retailer config move from code to DB once we exceed ~20 supported retailers?
- Is one-shot discovery good enough, or do users want a "find more retailers" button on existing products?
- Is a 1-hour manual-refresh cooldown the right balance, or do power users need 5 minutes?
- Should "Needs review" matches expire automatically after N days if untouched?
- Is the 3% trend deadband the right value, or should it scale with product price?
- Do we need a shared, anonymized cross-user price history (de-duplicated by URL) so new users get instant trend data?

---

*End of V1 PRD.*
