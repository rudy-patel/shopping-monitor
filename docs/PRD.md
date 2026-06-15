# Shopping Monitor — Product Requirements (V1)

> **Status:** Draft v1.4 — adds search-based product addition (T8.x) as a primary entry point alongside URL paste.
> **Implementation progress:** Task-level completion status and PR links live in [`docs/ROADMAP.md`](ROADMAP.md); chronological ship log in [`MEMORY.md`](../MEMORY.md).
> **Owner:** Product (you). **Audience:** Engineering, AI agents implementing the prototype.
> **Last updated:** 2026-06-15 (T8.2 search timeout second pass).

---

## 1. Overview

**Shopping Monitor** is a personal-use web app that gives a user **one organized home for everything they want to buy**. Search any product or paste a URL, and the app slots the item into the right category for you, watches its price and stock over time, surfaces the same product at up to four other Canadian retailers, and nudges you when something is genuinely worth buying — or quietly suggests letting go of items you've outgrown.

The product's pitch is **practicing healthy consumerism**: consolidate every "I want this" thought into one calm list, wait for the right sale, and avoid impulse purchases. The app is not a coupon firehose; it's a wishlist with price intelligence wrapped around it.

V1 is a free, low-traffic prototype optimized for a single primary user plus a handful of friends — not a public consumer product. We pay nothing for infrastructure, scraping, LLM, FX, or email in this phase.

---

## 2. Vision & Goals

### 2.1 Vision

A user searches for a thing they want (or pastes a URL if they already have one). The app quietly takes care of the rest — sorting the item into the right bucket, watching its price across retailers, telling the user when it's genuinely on sale, and gently checking in on items that have been on the list a long time. The result is a clean, organized wishlist of everything they're tracking that practices healthy consumerism by default.

### 2.2 V1 goals (in priority order)

1. **One organized home for things you want.** A self-organizing wishlist where searched or pasted products land in the right category automatically (with manual override) and are easy to scan and tend over time.
2. **Reliable price tracking** for a curated set of Canadian retailers, plus best-effort tracking of any other pasted URL.
3. **Multi-retailer comparison** on add: surface up to 4 alternates for the same product when they exist.
4. **Honest sale signal**: a clear, color-coded indicator of whether a product's price has trended down, up, or stayed flat over the past 30 days, plus opt-in notifications when a price meaningfully drops.
5. **Healthy-consumerism nudges.** Periodic revisit prompts that either celebrate a real sale on an old wishlist item or invite the user to let it go if it's been sitting unused.
6. **A clean, modern, snappy feel.** Light by default, shadcn/ui aesthetic, optimistic interactions, instant-feeling navigation.
7. **Frictionless sign-in** with Google so the user (and friends) can be onboarded in seconds.

### 2.3 Non-goals for V1 (explicit)

The following are deliberately **out of scope** for V1. They are documented in §13 so they aren't forgotten, but engineering should not build them in this phase.

- Shipping, tax, or duty calculation/estimation of any kind.
- A "price rating" that compares against MSRP or against prices at other retailers ("cheaper elsewhere"). V1 ships only a 30-day trend chip.
- Browser extension, mobile app, push notifications, SMS notifications.
- Sharing or collaborative lists between users.
- Public registration / anti-abuse / terms of service / GDPR tooling beyond basic auth + delete-my-account.
- Periodic re-discovery of new retailers for an existing product (one-shot at add time only).
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


| In scope                                                                                                                       | Out of scope                                                        |
| ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------- |
| Google SSO sign-in via Supabase                                                                                                | Email/password, magic links, other SSO                              |
| Per-user private shopping list                                                                                                 | Shared/collaborative lists                                          |
| Add product by pasting URL or by typing a free-text search query (LLM-grounded)                                                | Browser extension, share-sheet                                      |
| Search dialog: up to 5 candidate listings per query, supported + best-effort unsupported, 24h cache, Canadian-only             | Multi-page search, infinite scroll, saved searches                  |
| Variant inference from URL/page                                                                                                | Variant family grouping                                             |
| "Needs input" flag when variant unclear                                                                                        | Auto-guessing variants                                              |
| Daily scheduled price + stock scrape                                                                                           | Real-time / sub-daily monitoring                                    |
| Manual "refresh now" button (1-hour cooldown per product)                                                                      | Unlimited manual refresh                                            |
| Agentic cross-retailer discovery, one-shot at add                                                                              | Periodic re-discovery                                               |
| Up to 5 listings per product (1 user-pasted + up to 4 discovered)                                                              | Unlimited listings per product                                      |
| Auto-add high-confidence matches; queue medium-confidence for review                                                           | Auto-add everything                                                 |
| 30-day price trend chip (down / same / up) with color coding                                                                   | Historical price chart, MSRP comparison, cross-retailer rating      |
| Per-product notification threshold (default 20%, configurable)                                                                 | Per-listing thresholds, smart predictions                           |
| Daily digest email + persistent in-app notification list                                                                       | Per-event emails, push/SMS                                          |
| Back-in-stock notifications (separate from price drops)                                                                        | Real-time stock alerts                                              |
| 5 fixed categories: Clothing / Shoes / Home / Tech / Other, with **AI auto-categorization** on add (manual override available) | Custom user categories beyond the fixed 5; AI inventing new buckets |
| Archive (instead of delete) on purchase, with a history view                                                                   | Detailed purchase analytics                                         |
| CAD as canonical currency; cosmetic display-currency control in `/settings` with free FX API                                    | Multi-currency monitoring or thresholds                             |
| Revisit prompts: "still want this, it's on sale?" and "let this go?" for old wishlist items                                    | Behavioral analytics, in-depth purchase coaching                    |
| Light + dark theme with toggle in settings                                                                                     | System-theme auto-detection (V2)                                    |
| Local retailer fixture/mock harness so engineers and agents iterate without hitting real retailers                             | Recording new fixtures automatically from production scrapes        |


### 4.1 Implementation sequencing boundary

The PRD describes **complete V1**, but implementation should start with a **first integrated vertical slice** before parallel feature expansion. This slice is not a smaller product vision; it is the minimum path that proves the architecture end-to-end.

**First integrated vertical slice:**

- Google sign-in, profile bootstrap, and private user-owned data access.
- Core schema/migrations/RLS for profiles, products, listings, price history, notifications, and FX cache.
- Add-by-URL, product detail, dashboard, archive/restore/delete, category assignment, notification threshold, and fixture-backed scraping for **one established retailer**.
- Initial recommended retailer: `bestbuy_ca`, because it is a large Canadian retailer with enough bot-protection and structured-data variability to validate the scraper benchmark, fixture harness, and fallback strategy before expanding the registry.
- `SCRAPER_MODE=fixtures` works in local dev, CI, and automated agent tests with no outbound retailer requests.
- Scheduled scrape and fixed-time digest paths run against fixture data in tests.

After this slice is working, agents can expand in parallel across additional retailer modules, drift detection, and fixture coverage. Production validation (T6.2) is **done** for `bestbuy_ca` and `palmisleskate` on Render. Daily scrape (`0 8 * * *` UTC) and digest (`0 14 * * *` UTC) cron schedules are enabled (T6.3). Notification workflows through the daily digest job (T3.1–T3.6), the settings page (T4.2), and account deletion (T4.3) are shipped; deployment docs and production URLs are in `docs/DEPLOYMENT.md` (T6.1). Completing a reliable app with fewer retailers is higher priority than shipping many flaky retailer modules.


---

## 5. User Stories

Each story below is a V1 commitment.

### 5.1 Authentication

- **U-AUTH-1.** As a new user, I can sign in with my Google account in one click and land on an empty dashboard.
- **U-AUTH-2.** As a returning user, I stay signed in across sessions until I sign out.
- **U-AUTH-3.** As a user, I can delete my account from settings, which erases my products, listings, price history, and notifications.

### 5.2 Adding products

- **U-ADD-0.** As a signed-in user, I can open a global search overlay (header search bar or ⌘K / Ctrl+K) and type a free-text query (e.g. "AirPods Pro", "Nintendo Switch 2") to find matching listings across Canadian retailers — no URL required.
  - Up to 5 candidate listings are returned per query, ranked supported retailers first, then best-effort unsupported retailers.
  - Each result shows retailer label, title, optional brand hint, a one-line justification, and **Open** / **Track** actions.
  - Clicking **Track** uses the candidate URL as the primary listing and passes the remaining supported candidates as a `discovery_seed`, skipping the LLM `discover()` round-trip to stay within the Gemini free tier.
  - Search results are cached server-side by normalized query for 24 hours (`search_cache` table) to keep daily Gemini usage well inside the free quota.
  - An "Add by URL" fallback is always available from the dialog footer / empty state for users who already have a specific URL.
- **U-ADD-1.** As a signed-in user, I can paste a product URL into a single input and submit it.
- **U-ADD-2.** When I submit a URL from a natively supported retailer, the app extracts the title, image, current price, stock state, and variant attributes (size, color) and immediately creates a tracked product.
- **U-ADD-3.** If the URL specifies a variant via path/query, that variant is selected automatically.
- **U-ADD-4.** If the page has multiple variants and the URL is ambiguous, the app flags the product as **"Needs input"** and shows me a variant picker on a follow-up step.
- **U-ADD-5.** If the URL is from a retailer **not** on our supported list, the app still creates a tracked product using a best-effort generic scraper, and labels the listing "Generic scraper — may be unreliable."
- **U-ADD-6.** Immediately after I add a product, the app kicks off background cross-retailer discovery. I see a "Looking for other retailers…" indicator on the product card.
- **U-ADD-7.** When discovery completes, high-confidence matches are added automatically, medium-confidence matches go into a **"Needs review"** list under the product, and I receive an in-app notification telling me discovery finished.
- **U-ADD-8.** When I add a product, the app puts it into one of the 5 fixed categories automatically using AI on the page title, brand, and breadcrumbs. The Add Product modal defaults to auto-categorization (URL only); a **"Set category manually"** link reveals an optional category picker if I want to choose upfront. After add, the product detail page shows a brief **"Sorting into your list…"** shimmer on the category field (minimum ~2.5s) before revealing the assigned category, with a one-click override always available.
- **U-ADD-9.** As part of the same AI categorization step, the app produces a **short, human-friendly display title** for the product (e.g. *"Apple AirPods Pro 3 Noise Cancelling True Wireless Earbuds with MagSafe Charging Case"* → *"Apple AirPods Pro 3"*). The cleaned title is only adopted when it is strictly shorter than the scraped title; otherwise the original title is kept. The original scraped title remains preserved on the underlying listing for traceability. This adds **zero** Gemini calls — the cleaned title rides on the same structured-JSON categorization response.

### 5.3 Viewing & organizing products

- **U-VIEW-1.** My default dashboard shows all active products grouped by the 5 fixed categories. Each category section is collapsible (Notion-style toggle). All five categories are always visible — empty ones show a zero count and start collapsed. **Edit order** mode lets me drag category headers to reorder sections (saved locally) and drag products within a category (saved per product via `dashboard_sort_order`; cross-category moves use the product detail category field).
- **U-VIEW-2.** I can toggle to a flat list view and filter by category, retailer, or "has unreviewed matches."
- **U-VIEW-3.** Each product row shows: title, brand, retailer of best current price (with a small bundled icon for supported retailer slugs), best current price (in display currency), 30-day trend chip, alternate retailers count, last-refreshed timestamp, manual refresh button, and a kebab menu. V1 list surfaces are typography-first — no in-app product images; users open the retailer PDP via listing links when they want to see photos.
- **U-VIEW-4.** Clicking a row opens a product detail page showing every listing as a card with retailer (icon + label linking to the source URL with an external-link icon for supported slugs), current price (prominent), stock state, and last-refreshed timestamp (no inline product images in-app; scrape status is stored but not shown on listing cards). The detail page hero sits in a light bordered card: editable product title (**Rename** when AI cleanup or the scraped name is wrong), best price (tinted by 30-day trend) and best retailer, trend chip (with optional `delta_pct` suffix), discovery status beside the chip (hidden once complete), compact 30-day sparkline, and a metadata row (category pill, tracking-since date, last refresh). Archived products grey the sparkline and show "Tracking paused." Products with fewer than 7 days of data render a flat sparkline at the current best price so the chip and the line agree visually. Listings and Settings follow below with tighter vertical rhythm; Settings is collapsed by default behind a chevron. On mobile, the sticky action bar repeats price + trend chip beside Refresh/Archive/Delete.
- **U-VIEW-5.** I can manually re-categorize a product into a different fixed bucket from its detail page.
- **U-VIEW-5b.** I can rename a product from its detail page when the auto-generated title is too long or wrong. The new name appears on the dashboard and in delete confirmations. Refresh and scheduled scrapes do not overwrite a manual rename; the original scraped title stays on the listing snapshot.
- **U-VIEW-6.** I can edit a product's notification threshold from its detail page (overriding my global default). The field shows a computed dollar trigger (e.g. "Alert when below $223.99 (20% off $279.99)") based on the rolling baseline and effective threshold %.
- **U-VIEW-7.** I can manually refresh a product (forces a fresh scrape of every listing) with a 1-hour per-product cooldown.

### 5.4 Cross-retailer comparison

- **U-CMP-1.** On a product detail page, listings are sorted by current price ascending so the cheapest is always on top.
- **U-CMP-2.** Each listing shows confidence score (for non-primary listings), retailer name (linked to the source URL), current price, stock state, and a "Remove this match" button.
- **U-CMP-3.** I can review the "Needs review" queue per product: each candidate shows the candidate URL's title, image, price, and reason for the medium confidence. I accept, reject, or open the URL for closer inspection.
- **U-CMP-4.** When a product has multiple active listings, the cheapest card is subtly highlighted (left accent + "Best price" badge) and every more expensive card shows a small `+$N vs best` delta label.

### 5.5 Price trend & sale signal

- **U-TREND-1.** Every active product shows one of three chips:
  - **Green** "Down in the last 30 days"
  - **Neutral** "Same in the last 30 days" (also the default when we have less than 7 days of data)
  - **Red** "Up in the last 30 days"
- **U-TREND-2.** The trend is computed from the product-level daily minimum price over a rolling 30-day window (see §7.4 for the exact rule).

### 5.6 Notifications

- **U-NOT-1.** When the best price for a product drops by ≥ the product's threshold (default 20%) relative to its rolling-30-day baseline, the user gets one notification (in-app + included in next day's email digest).
- **U-NOT-2.** When any listing transitions from out-of-stock to in-stock, the user gets a separate "Back in stock" notification.
- **U-NOT-3.** All notifications appear in a persistent in-app **Notifications** page (bell icon in header), with read/unread state, sorted newest-first, retained for 90 days.
- **U-NOT-4.** Once per day, the user receives an email digest summarizing all unread notifications since the previous digest. The digest is suppressed entirely if there are zero events.
- **U-NOT-5.** I can disable notifications globally or per product. I can edit my default threshold and per-product overrides in settings.

### 5.7 Currency display

- **U-CUR-1.** Prices are stored and computed in **CAD** always. All thresholds and trend math operate on the CAD value.
- **U-CUR-2.** `/settings` is the sole display-currency control; default is CAD. Supported display currencies in V1: CAD, USD, EUR, GBP. (More can be added trivially.)
- **U-CUR-3.** Conversion uses a free FX API (see §10.5). Rates are cached for 24 hours. Conversion failures fall back silently to CAD display.

### 5.8 Archiving & purchase history

- **U-ARC-1.** I can archive a product from its detail page or card kebab menu (e.g., after buying it). Archiving shows a success toast and keeps me on the current page (dashboard or product detail); I can open **History** from nav when I want to browse archived items.
- **U-ARC-2.** Archived products move to a separate **History** view; they retain all stored price history and listings.
- **U-ARC-3.** I can restore an archived product to "active."
- **U-ARC-4.** I can permanently delete a product (irreversible).

### 5.9 Settings

- **U-SET-1.** Settings include: display currency, global notifications on/off, global default notification threshold %, daily email digest on/off, light/dark theme toggle, revisit-prompt cadence + on/off, and a delete-account entry point (`DELETE /api/account` with confirmation dialog).

### 5.10 Revisit prompts (healthy-consumerism nudges)

- **U-REV-1.** When an item has been on my list for ≥ 30 days and is currently ≥ 15% below its 30-day baseline, I get a playful "still want this? it's on sale" prompt in the next daily digest and in-app, with one-click buttons to keep tracking or archive.
- **U-REV-2.** When an item has been on my list for ≥ 30 days with no recent interaction (no manual refresh, no threshold edits, no acceptance of discovered listings), I get a gentle "let this go?" prompt with one-click archive.
- **U-REV-3.** I can change the stale-prompt threshold (default 30 days), disable revisit prompts entirely, or disable just one of the two prompt types from settings.
- **U-REV-4.** Revisit prompts never repeat for the same product within 30 days, and the tone of all prompt copy is playful, empathetic, and human — never robotic or guilt-trippy.

---

## 6. Information Architecture

V1 frontend routes (all behind auth except `/login`):


| Route                    | Purpose                                                                                              |
| ------------------------ | ---------------------------------------------------------------------------------------------------- |
| `/login`                 | Google SSO landing — warm splash with dashed **Someday.** pill, rotating taglines, and desktop-only decorative price/wishlist stickers |
| `/`                      | Dashboard, default = grouped by category                                                             |
| `/list`                  | Flat list + filters                                                                                  |
| `/products/:id`          | Product detail (listings, history, settings, needs-review queue)                                     |
| `/products/:id/variants` | Variant picker for "Needs input" products                                                            |
| `/notifications`         | Bell-icon page; full notification log                                                                |
| `/history`               | Archived products                                                                                    |
| `/settings`              | Global preferences (currency, threshold, digest, theme, revisit prompts) + delete account |


A persistent top nav contains: app title/logo, a header **Search** trigger (⌘K / Ctrl+K, mobile: icon-only), "Add Product" CTA, bell icon (notifications), avatar menu (settings, sign out).

The header **Search** trigger opens a command-palette-style overlay with a free-text input; results render inline with one-click **Track** per row and an "Add by URL" fallback. The "Add Product" CTA continues to open the URL-input modal for users who already have a specific URL.

---

## 7. Functional Requirements

### 7.1 Authentication

- Supabase Auth with Google as the **only** enabled provider.
- Frontend uses `@supabase/supabase-js` for client-side session.
- Backend validates the user's Supabase JWT on every API call using JWKS (see `docs/AUTHENTICATION.md`). `AUTH_BYPASS_ENABLED=true` is permitted in local dev only and uses a fixed dev user UUID.
- On first sign-in, a row is upserted into `profiles` with defaults (see §8.1).
- Delete-account flow: `DELETE /api/account` calls Supabase Auth admin `delete_user`; Postgres `ON DELETE CASCADE` from `auth.users` removes the user's `profiles`, `products`, `product_listings`, `price_history`, and `notifications` rows. Disabled when `AUTH_BYPASS_ENABLED=true`. Hard-denied identities are listed in `backend/core/protected_accounts.py`.

### 7.2 Product addition

**Two entry points (both end in the same backend pipeline):**

- **URL paste** (header **Add Product** modal) — user already has a specific product URL.
- **Free-text search** (header search bar / ⌘K command palette, §5.2 U-ADD-0) — user types a query; the LLM returns up to 5 ranked candidate listings; one click on **Track** posts the chosen URL plus the other supported candidates as `discovery_seed`. The seed lets the discovery job skip its own LLM call (cost control, see §10.7).

**Adding flow (synchronous portion):**

1. Frontend POSTs `{ url, category?, discovery_seed? }` to `POST /api/products`. `category` is optional — populated when the user explicitly picked a category in the Add modal; omitted (or `"auto"`) means defer to AI categorization. `discovery_seed` is optional — populated only by the search flow with up to 4 pre-vetted candidates `[{retailer_slug, url}, ...]` to short-circuit the discovery LLM call.
2. Backend identifies the retailer by matching `url` against the supported-retailer registry (see §11). If no match, falls back to the `generic` scraper.
3. Backend invokes the retailer's scraper to extract: `title`, `brand`, `image_url`, `current_price_cad`, `currency_seen`, `is_in_stock`, `available_variants` (list of `{attribute_name, attribute_value}`), `selected_variant` (if inferable from URL), and `breadcrumbs` (best-effort).
4. **Categorization (§7.7)** runs synchronously: if the request supplied a category, use it (`category_source='manual'`); otherwise call the LLM categorizer with `title`/`brand`/`retailer_slug`/`breadcrumbs` under a 1.5s timeout, falling back to the heuristic (and ultimately `other`) if needed. The resolved `category` and `category_source` are set on the new product row.
5. Backend creates one `products` row and one `product_listings` row (the user-pasted URL, marked `is_primary=true`).
6. If `selected_variant` is unambiguous → product status = `active`. If multiple variants and URL is ambiguous → product status = `needs_input`; the variant picker route loads `available_variants` from the listing's stored snapshot.
7. Backend records the first `price_history` snapshot.
8. Backend enqueues the cross-retailer discovery job (see §7.3) and returns the new product to the client. The client navigates to `/products/:id`. When a `discovery_seed` was provided, the discovery job uses the seed URLs directly and does **not** call the LLM `discover()` endpoint; the same scrape/score/auto-add/cap pipeline still runs.

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
5. **Auto-add** candidates with score ≥ 0.85, up to a cap of 4 non-primary listings (5 total per product). **Queue** candidates with 0.6 ≤ score < 0.85 to the product's "Needs review" list. **Discard** the rest. Needs-review candidates are stored as `product_listings` rows with `review_status='needs_review'` and count toward the 5-listing cap until accepted, rejected, or deleted.
6. Stop scoring more candidates as soon as the auto-add cap is hit.
7. Mark the discovery job complete on the `products` row and write an in-app notification to the user.

**Failure handling:** if the LLM returns no candidates or the call fails, log a warning and complete the discovery job silently — the user keeps their single primary listing.

**Cost control:** discovery is one-shot per product (never re-runs automatically). The user can force a re-discovery by deleting and re-adding the product. This caps Gemini-free-tier spend at one call per product creation.

### 7.4 Price monitoring & trend

**Daily scrape job (GitHub Actions cron, `0 8 * * *` UTC, ~04:00 America/Toronto):**

1. Fetch every `product_listings` row for products in `active` or `needs_input` status (includes rejected listings; excludes archived products).
2. For each, invoke the appropriate retailer scraper (or the generic scraper).
3. Persist a `price_history` row with the observed price, stock state, and timestamp (`source = scheduled`).
4. Update the listing's `last_known_price_cents`, `is_in_stock`, `last_scraped_at`, and `scrape_status` columns.
5. Increment `scrape_failure_count` on failure; reset to 0 on success.
6. After all scrapes finish, evaluate scrape-triggered notification types (`price_drop`, `back_in_stock`, `scrape_failing`) for products touched in this run only.
7. Evaluate revisit-prompt triggers (§7.10) for every active product per user whose owner has revisit prompts enabled, writing in-app notification rows.
8. Stop. Email sending is handled by the separate digest job below so users receive messages at a predictable morning time rather than immediately after the scrape.

**Implementation notes (T3.5):** Entry point is `POST /internal/jobs/scrape-all` (worker token). A Postgres advisory lock prevents duplicate concurrent runs. GitHub Actions workflow `.github/workflows/scrape.yml` runs on `workflow_dispatch` and cron `0 8 * * *` UTC (enabled T6.3). Scheduled scrape-all does not update `products.last_refresh_at` or `last_user_interaction_at` (those remain manual-refresh / user-interaction timestamps).

**Manual refresh:**
Endpoint `POST /api/products/:id/refresh`. Cooldown = `products.last_refresh_at` must be ≥ 1 hour ago. Runs the same scrape logic synchronously across the product's listings, returns updated state, evaluates notification triggers for that product only.

**Product-level daily minimum:** For each product/day, compute the lowest in-stock CAD price observed across eligible listings (`review_status IN ('auto_added', 'accepted')`; primary listings use `accepted`). Needs-review and rejected listings do not affect the displayed best price, trend, thresholds, or notifications until accepted, although needs-review rows still count toward the listing cap.

**Trend computation:** For each product, use the product-level daily minimum over the past 30 days. Compute:

- `delta_pct = (price_today - price_30d_ago) / price_30d_ago`

If we have **< 7 days** of history: chip = **neutral / "Same in the last 30 days."**
Else if `delta_pct <= -0.03`: chip = **green / "Down in the last 30 days."**
Else if `delta_pct >= +0.03`: chip = **red / "Up in the last 30 days."**
Else: chip = **neutral / "Same in the last 30 days."**

(The ±3% deadband prevents flapping for trivial fluctuations.)

### 7.5 Notification triggers

Evaluated after every successful scrape (scheduled or manual).

**Price-drop trigger:**

- Skip entirely if `profiles.notifications_enabled = false` or `products.notifications_enabled = false`.
- Let `baseline = MAX(product-level daily minimum)` over the trailing 30 days, restricted to in-stock observations from accepted/auto-added/primary listings.
- Let `current = newest product-level daily minimum` for the product.
- If `(baseline - current) / baseline ≥ product.notification_threshold_pct / 100`, fire a `price_drop` notification.
- **Debounce:** suppress if a `price_drop` notification was already created for this product in the last 24 hours.

**Back-in-stock trigger:**

- Skip entirely if `profiles.notifications_enabled = false` or `products.notifications_enabled = false`.
- Fire a `back_in_stock` notification when any listing's `is_in_stock` transitions from `false` to `true`.
- Debounce: suppress if a `back_in_stock` notification was already created for the same listing in the last 24 hours.

**Other notification types:**

- `discovery_complete` — written exactly once when cross-retailer discovery finishes.
- `needs_input` — written exactly once when a product is created in `needs_input` status.
- `scrape_failing` — written when a listing fails 3 consecutive scheduled scrapes; user can hide it from settings if noisy.
- `revisit_on_sale` — written when a product on the list ≥ 30 days is currently ≥ 15% below its 30-day baseline. See §7.10.
- `revisit_stale` — written when a product on the list ≥ `profiles.revisit_stale_days` days has no recent user interaction. See §7.10.

### 7.6 Email digest

- Sent at most once per day, by a separate GitHub Actions cron at `0 14 * * *` UTC. This is a fixed UTC time chosen to land in the Pacific morning; V1 does not implement timezone or daylight-saving adjustments.
- Provider: **Resend** free tier (see §10.4). Pluggable behind a `MailService` interface so providers can swap.
- Template: plain text + simple HTML. Lists each event with product title, change summary, and a deep link back to the app.
- Skipped entirely if the user has zero unread notifications since the previous digest, or if they have email notifications disabled.

### 7.7 Categories

- Five fixed categories: `clothing`, `shoes`, `home`, `tech`, `other`. AI is **not** allowed to invent new categories in V1; the categorizer must return exactly one of these five slugs.
- The Add Product modal defaults to **auto-categorization** (URL input only). A **"Set category manually"** disclosure reveals an optional category picker; if the user picks a category there, that wins and no LLM call is made.
- If auto mode is used, category assignment runs **synchronously** as part of the add request, in this priority order:
  1. **LLM categorizer** (Gemini Flash via `LlmProvider`, see §10.7) given the scraped `title`, `brand`, `retailer_slug`, and any retailer breadcrumbs. The prompt hard-instructs the model to choose exactly one of the 5 slugs **and** to return a short, human-friendly `clean_title` (4–80 chars) for the product (U-ADD-9). Both fields are returned as a single structured-JSON response — title cleanup adds zero extra Gemini requests.
  2. **Heuristic fallback** (retailer-slug default → breadcrumb keyword match → title/brand keyword match → retailer's mapped category) if the LLM call fails, times out, returns an invalid slug, or quota is exhausted. The heuristic does not produce a `clean_title`; the scraped title is kept verbatim in that case.
  3. **`other`** if even the heuristic can't classify.
- The whole categorization step is wrapped in a **1.5s timeout** so the add flow stays responsive and degrades gracefully to the heuristic on slow days. After navigation to product detail, the category field shows a **minimum ~2.5s** client-side "Sorting into your list…" shimmer (shared with the dashboard row badge for the same product) so the auto-sort feels intentional; this does **not** add extra Gemini calls.
- The `clean_title` from the LLM response is adopted as `products.title` only when it's non-empty, not equal to the scraped title (case-insensitive), and **strictly shorter** than the scraped title. Otherwise the scraped title is kept. The original scraped title is always preserved verbatim in `product_listings.scrape_snapshot.title` for traceability and as the rollback source if a future feature lets users revert manual renames.
- The user can re-categorize from the product detail page at any time. Manual overrides are sticky — the categorizer never reruns automatically and won't undo a manual choice.
- All category-assignment logic lives behind a single `Categorizer` interface so swapping providers or adding a "suggest with confidence" mode in V2 is a no-schema change.

### 7.8 Generic fallback scraper

For URLs from any unsupported retailer:

- Use the shared scraper pipeline (§10.6), starting with a lightweight browser-like HTTP request (`curl_cffi` preferred for TLS/browser impersonation; `httpx` acceptable only for sites that do not block it).
- Apply schema.org `Product` JSON-LD extraction first (most retailers expose this).
- Fall back to OpenGraph tags (`og:title`, `og:image`, `og:price:amount`, `og:price:currency`, `product:availability`).
- If neither yields a price, mark the listing `scrape_status='blocked'` and surface "Couldn't read price from this site" to the user; product stays in their list with manual refresh available.

The generic scraper never participates in cross-retailer discovery (it can't reliably normalize variants).

### 7.9 Scraper benchmark pipeline

**Status (2026-06-14):** Harness implemented (ROADMAP T5.1). Fixture catalog covers production retailers through T5.4 (`amazon_ca`, `nike_ca`); reports live in `docs/benchmarks/`. Regenerate with `make benchmark-retailers`. Deferred §11 retailers: `sportchek`, `footlocker_ca`, `costco_ca`, `oakley`, `canadiantire`, `vans_ca`, `eatyourwater`.

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

### 7.10 Revisit prompt evaluation

Runs once per day after the daily scrape, before digest send.

**Eligibility filter:**

- Only `status = 'active'` products are considered.
- The user must have `profiles.revisit_prompts_enabled = true`.
- A product is only ever revisited if no `revisit_on_sale` or `revisit_stale` notification has fired for it in the previous 30 days (debounce).

**`revisit_on_sale` trigger:**

- `now() - products.created_at >= 30 days`.
- `profiles.revisit_on_sale_enabled = true`.
- The product's current product-level daily minimum is at least 15% below the 30-day rolling baseline (same baseline definition as §7.5 price-drop).
- At least one accepted/auto-added/primary listing contributing to the product-level daily minimum is currently in stock.
- The user has not already received a regular `price_drop` notification for this product in the last 7 days (so we don't double-ping on the same event).

**`revisit_stale` trigger:**

- `now() - products.created_at >= profiles.revisit_stale_days` (default 30).
- `profiles.revisit_stale_enabled = true`.
- `products.last_user_interaction_at IS NULL` OR `now() - products.last_user_interaction_at >= profiles.revisit_stale_days`.
- "Interaction" = manual refresh, threshold edit, category change, listing accept/reject, archive/restore, or mark-read of any notification for this product.
- Stale prompts are mutually exclusive with `revisit_on_sale` on the same product on the same day; if both would fire, only `revisit_on_sale` is created.

**Surfaces:**

- Each revisit prompt is written as a row in `notifications` (in-app) AND included in the next daily digest if the user has email digests enabled. This keeps revisit nudges consistent with every other notification type.
- Each prompt includes one-click actions (`Keep on list`, `Archive it`). The `Archive` action sets `products.status = 'archived'` and writes `products.last_user_interaction_at = now()`. The `Keep on list` action just marks the notification read and writes `last_user_interaction_at = now()` so the same product won't qualify for `revisit_stale` again immediately.

**Copy guidelines:**

- Playful, empathetic, human. Avoid robotic, fake-friendly, or guilt-trippy phrasings.
- No exclamation marks in default microcopy. No fake urgency.
- Final copy lives in the frontend, not this doc, but reviewers should hold the bar at these examples or better:
  - On-sale: "This has been quietly waiting on your list for a month and it's now {{pct}}% off. Worth a second look?"
  - Stale: "Past you wanted this {{days}} days ago. Still feeling it, or time to let it go?"

---

## 8. Data Model

All new tables live in `public` with **RLS enabled** per `docs/DATABASE.md`. Migrations are added under `backend/db/migrations/` in numeric order. All timestamps are `TIMESTAMPTZ`. Prices are stored as integer cents in CAD; never floats.

### 8.1 `profiles`


| Column                     | Type          | Notes                                                                                               |
| -------------------------- | ------------- | --------------------------------------------------------------------------------------------------- |
| `user_id`                  | `uuid` PK     | References `auth.users(id)` ON DELETE CASCADE                                                       |
| `display_currency`         | `text`        | Default `'CAD'`. Allowed: CAD, USD, EUR, GBP.                                                       |
| `default_threshold_pct`    | `int`         | Default `20`. Range 1–95.                                                                           |
| `notifications_enabled`    | `bool`        | Default `true`. Master switch for in-app notifications and notification-trigger evaluation.         |
| `email_digest_enabled`     | `bool`        | Default `true`.                                                                                     |
| `theme`                    | `text`        | `'light'` or `'dark'`. Default `'light'`. Drives the `dark` class on the frontend `<html>` element. |
| `revisit_prompts_enabled`  | `bool`        | Default `true`. Master switch for §7.10.                                                            |
| `revisit_on_sale_enabled`  | `bool`        | Default `true`. Disables only the `revisit_on_sale` prompt type.                                    |
| `revisit_stale_enabled`    | `bool`        | Default `true`. Disables only the `revisit_stale` prompt type.                                      |
| `revisit_stale_days`       | `int`         | Default `30`. Range 7–365.                                                                          |
| `created_at`, `updated_at` | `timestamptz` |                                                                                                     |


**RLS:** Pattern A — users select/update their own row.

### 8.2 `products`


| Column                       | Type          | Notes                                                                                                                                                                                   |
| ---------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`                         | `uuid` PK     |                                                                                                                                                                                         |
| `user_id`                    | `uuid`        | FK to `auth.users`, indexed                                                                                                                                                             |
| `title`                      | `text`        |                                                                                                                                                                                         |
| `brand`                      | `text`        | nullable                                                                                                                                                                                |
| `image_url`                  | `text`        | nullable                                                                                                                                                                                |
| `category`                   | `text`        | enum-like; one of `clothing/shoes/home/tech/other`                                                                                                                                      |
| `status`                     | `text`        | `active`, `needs_input`, `archived`                                                                                                                                                     |
| `notification_threshold_pct` | `int`         | nullable; falls back to `profiles.default_threshold_pct`                                                                                                                                |
| `notifications_enabled`      | `bool`        | Default `true`.                                                                                                                                                                         |
| `discovery_status`           | `text`        | `pending`, `running`, `complete`, `failed`                                                                                                                                              |
| `category_source`            | `text`        | `manual`, `llm`, `heuristic`, `default_other`. Used to skip future auto-categorization when value is `manual`.                                                                          |
| `last_refresh_at`            | `timestamptz` | nullable; used to enforce manual refresh cooldown                                                                                                                                       |
| `last_user_interaction_at`   | `timestamptz` | nullable; updated on manual refresh, threshold/category edits, listing accept/reject, archive/restore, or notification mark-read for this product. Used by §7.10 stale revisit prompts. |
| `created_at`, `updated_at`   | `timestamptz` |                                                                                                                                                                                         |


**RLS:** Pattern A. Index on `(user_id, status)`.

### 8.3 `product_listings`


| Column                     | Type           | Notes                                                |
| -------------------------- | -------------- | ---------------------------------------------------- |
| `id`                       | `uuid` PK      |                                                      |
| `product_id`               | `uuid`         | FK products, indexed                                 |
| `retailer_slug`            | `text`         | e.g. `amazon_ca`, `nike_ca`, `generic`               |
| `url`                      | `text`         | the canonical product URL                            |
| `variant_attributes`       | `jsonb`        | e.g. `{"size":"10","color":"white"}`                 |
| `available_variants`       | `jsonb`        | nullable list of variant combinations from the latest scrape; used by the variant picker when `products.status='needs_input'` |
| `scrape_snapshot`          | `jsonb`        | nullable normalized raw fields from the latest successful scrape for debugging/fixture parity, excluding full HTML |
| `is_primary`               | `bool`         | true for the URL the user pasted                     |
| `match_confidence`         | `numeric(4,3)` | nullable; only set for discovered listings           |
| `review_status`            | `text`         | `auto_added`, `needs_review`, `accepted`, `rejected`; primary listings use `accepted` |
| `last_known_price_cents`   | `int`          | nullable; CAD cents                                  |
| `is_in_stock`              | `bool`         | nullable until first scrape                          |
| `last_scraped_at`          | `timestamptz`  |                                                      |
| `scrape_status`            | `text`         | `ok`, `failing`, `blocked`                           |
| `scrape_failure_count`     | `int`          | default 0                                            |
| `created_at`, `updated_at` | `timestamptz`  |                                                      |


Needs-review listings count toward the 5-listing cap but are excluded from best-price, trend, threshold, digest, and stock notification calculations until accepted. Rejected listings remain for audit/debugging unless hard-deleted, but never count toward user-facing price calculations.

**RLS:** Pattern A via join on `products.user_id`.

### 8.4 `price_history`


| Column        | Type           | Notes                        |
| ------------- | -------------- | ---------------------------- |
| `id`          | `bigserial` PK |                              |
| `listing_id`  | `uuid`         | FK product_listings, indexed |
| `price_cents` | `int`          | CAD cents, NOT NULL          |
| `is_in_stock` | `bool`         |                              |
| `observed_at` | `timestamptz`  | indexed                      |
| `source`      | `text`         | `scheduled`, `manual`        |


**RLS:** Pattern A via join. Retain forever in V1 (volume is tiny — one row per listing per day, ~365 rows per listing per year).

### 8.5 `notifications`


| Column          | Type          | Notes                                                                                                                    |
| --------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `id`            | `uuid` PK     |                                                                                                                          |
| `user_id`       | `uuid`        | FK auth.users                                                                                                            |
| `product_id`    | `uuid`        | nullable                                                                                                                 |
| `listing_id`    | `uuid`        | nullable                                                                                                                 |
| `type`          | `text`        | `price_drop`, `back_in_stock`, `discovery_complete`, `needs_input`, `scrape_failing`, `revisit_on_sale`, `revisit_stale` |
| `payload`       | `jsonb`       | type-specific data (old price, new price, retailer, etc.)                                                                |
| `is_read`       | `bool`        | default false                                                                                                            |
| `email_sent_at` | `timestamptz` | nullable; populated when included in a digest                                                                            |
| `created_at`    | `timestamptz` | indexed                                                                                                                  |


**RLS:** Pattern A.

### 8.6 `fx_rates_cache`

Backend-only table; Pattern B (service-role-only).


| Column       | Type                         |
| ------------ | ---------------------------- |
| `pair`       | `text` PK (e.g. `'CAD_USD'`) |
| `rate`       | `numeric`                    |
| `fetched_at` | `timestamptz`                |


### 8.7 `search_cache`

Backend-only table; Pattern B (service-role-only). Caches LLM search results by normalized query hash so the same query within the TTL window does not re-burn Gemini quota.


| Column           | Type          | Notes                                                                                  |
| ---------------- | ------------- | -------------------------------------------------------------------------------------- |
| `query_hash`     | `text` PK     | SHA-256 of `normalize_query(query)`                                                    |
| `query`          | `text`        | Original normalized query (lowercase, collapsed whitespace) for diagnostics            |
| `result_payload` | `jsonb`       | Serialized `LlmSearchResult` (candidates + provider metadata)                          |
| `fetched_at`     | `timestamptz` | Insert/refresh time; entries are considered expired after `SEARCH_CACHE_TTL_HOURS` (default 24h). Indexed |


**Retailer config does not live in the DB** in V1 — it's a Python module so adding a retailer is a code change reviewed in PR (intentional; see §11).

---

## 9. API Surface

REST under `/api`, all behind auth (Supabase JWT).


| Method   | Path                                            | Purpose                                                                     |
| -------- | ----------------------------------------------- | --------------------------------------------------------------------------- |
| `POST`   | `/api/search`                                   | LLM-grounded free-text product search (24h server cache)                    |
| `POST`   | `/api/products`                                 | Add a new product from a URL (optionally with `discovery_seed`)             |
| `GET`    | `/api/products`                                 | List user's products with filters (`status`, `category`)                    |
| `GET`    | `/api/products/:id`                             | Product detail (includes listings + 30-day daily-minimum price history)     |
| `PATCH`  | `/api/products/:id`                             | Update category, threshold, notifications-enabled, status (archive/restore) |
| `PUT`    | `/api/products/dashboard-order`                 | Bulk update `dashboard_sort_order` for manual dashboard row ordering within a category |
| `DELETE` | `/api/products/:id`                             | Hard delete                                                                 |
| `POST`   | `/api/products/:id/refresh`                     | Trigger manual refresh (enforces 1h cooldown)                               |
| `POST`   | `/api/products/:id/select-variant`              | Resolve `needs_input` by selecting a variant                                |
| `POST`   | `/api/products/:id/listings/:listing_id/accept` | Accept a `needs_review` discovery candidate                                 |
| `POST`   | `/api/products/:id/listings/:listing_id/reject` | Reject one                                                                  |
| `DELETE` | `/api/products/:id/listings/:listing_id`        | Remove a non-primary listing                                                |
| `GET`    | `/api/notifications`                            | Paginated notification list                                                 |
| `POST`   | `/api/notifications/mark-read`                  | Bulk mark-read                                                              |
| `POST`   | `/api/notifications/:id/action`                 | Handle one-click notification actions such as revisit `keep` or `archive`   |
| `GET`    | `/api/profile`                                  | Current user's settings                                                     |
| `PATCH`  | `/api/profile`                                  | Update settings                                                             |
| `DELETE` | `/api/account`                                  | Delete account + all data                                                   |
| `GET`    | `/api/fx/rates`                                 | Convenience: current FX rates for supported display currencies              |


Internal (service-role, called from GitHub Actions worker, not exposed to browser):


| Method | Path                          | Purpose                  |
| ------ | ----------------------------- | ------------------------ |
| `POST` | `/internal/jobs/scrape-all`   | Daily worker entry point |
| `POST` | `/internal/jobs/send-digests` | Daily worker entry point |


Internal endpoints require a shared-secret header (`X-Worker-Token`).

---

## 10. Tech Stack & System Design

### 10.1 Frontend

- **React + Vite + TypeScript** (already scaffolded in `frontend/`).
- **State/data:** TanStack Query for server data; React Context for session, display currency, and theme.
- **UI library:** Tailwind CSS + **shadcn/ui** (committed, not "or similar"). `sonner` for toasts.
- **Motion:** Framer Motion for state transitions (item add, category change, notification appear). Subtle, never showy.
- **Theme:** Light by default with a toggle in `/settings` that writes `profiles.theme` and applies the `dark` class on `<html>`. No system-theme auto-detection in V1.
- **Auth:** `@supabase/supabase-js` with Google OAuth.
- **Hosting:** Vercel free tier per `docs/DEPLOYMENT.md`.

**Design principles (V1):**

1. **Minimal and modern.** Monochrome base, generous whitespace, one accent color, shadcn's default radius and typography. Resist adding chrome.
2. **Snappy by default.** Every user action surfaces visible feedback within 100ms. Mutations are optimistic; only roll back on server error. Skeleton loaders, never spinners, for first-paint and route changes. Refresh actions show inline skeleton shimmer and “Refreshing…” copy.
3. **Calm voice.** Microcopy is playful and empathetic (see §7.10 revisit prompts). No exclamation marks in default UI strings, no robotic tone, no fake urgency.
4. **Content over chrome.** The category-grouped dashboard is the hero surface; nav is a thin, persistent top bar with a mobile bottom tab bar for primary routes.
5. **Typography-first lists.** Product rows are text-only in-app (no scraped thumbnails). Trend chips use subtle green/yellow/red tints (down/same/up) with readable labels; stock chips stay monochrome.
6. **Accessible.** Color-coded chips always pair with text. Lighthouse Performance and Accessibility ≥ 95 are hard targets (see §12). Vitest axe checks on key routes.
7. **One keyboard shortcut: ⌘K / Ctrl+K opens the global search overlay.** This is the single command-palette-style affordance in V1; everything else is mouse and touch first-class. Other keyboard shortcuts are deferred to V2.

### 10.2 Backend

- **FastAPI** (existing `backend/main.py`). Python 3.12.
- **Auth:** Supabase JWT validation via JWKS, per `docs/AUTHENTICATION.md`.
- **DB client:** `supabase-py` (service-role for backend writes; PostgREST-via-RLS optional).
- **Hosting:** Render free tier (web service). The free tier sleeps after 15 minutes idle; first request after sleep is slow. Acceptable for V1.

### 10.3 Background jobs

- **Daily scrape runner:** GitHub Actions workflow under `.github/workflows/scrape.yml`, scheduled at `0 8 * * *` UTC (≈ 04:00 America/Toronto). Also supports `workflow_dispatch`. Production `workflow_dispatch` verified 2026-06-14 (see `docs/DEPLOYMENT.md`); cron enabled T6.3 (2026-06-15).
- **Daily digest runner:** GitHub Actions workflow under `.github/workflows/digest.yml`, scheduled at `0 14 * * *` UTC. Also supports `workflow_dispatch`. Cron enabled T6.3 (2026-06-15). This is a fixed UTC time chosen to land in the Pacific morning and keeps V1 simple by avoiding timezone/daylight-saving scheduling.
- **Action entrypoints:** small Python scripts in `backend/workers/` call the deployed backend's internal endpoints (`POST /internal/jobs/scrape-all`, `POST /internal/jobs/send-digests`) with `X-Worker-Token` from `WORKER_TOKEN`.
- **Business logic location:** the real scrape, notification, revisit, and digest logic lives in importable backend service modules used by the FastAPI internal endpoints. Worker scripts stay thin wrappers around HTTP calls so deployed jobs exercise the same path as production, while unit tests can call service modules directly with fixtures.
- **Repository visibility:** public GitHub repository is preferred if Actions minutes ever become a free-tier constraint. A private repository is acceptable while included free minutes comfortably cover once-daily jobs.
- **Headless browser for protected sites:** `playwright` in the backend, used only by retailers that need JavaScript execution or cannot be handled by structured data / `curl_cffi`. Render free tier can run Playwright (with installed deps in the build step), but cold starts and memory pressure make it a fallback, not the default.
- **Rationale for this split:** GitHub Actions provides free scheduling with visible workflow logs; the backend hosts the actual logic and DB credentials. This avoids duplicating scraping code between an Actions runner and the API.

### 10.4 Email

- **Provider:** Resend free tier (3,000 emails/month, 100/day). Requires a verified domain or use Resend's `onboarding@resend.dev` sandbox sender for V1 if no domain is wired up.
- **Sent by:** the daily digest worker (`POST /internal/jobs/send-digests`), triggered by the GitHub Actions cron in §10.3. V1 sends one fixed Canada-wide morning digest and does not implement per-user timezone scheduling.

### 10.5 FX rates

- **Provider:** Frankfurter (`api.frankfurter.dev/v1`, free, no key, ECB rates). Primary.
- **Fallback:** ExchangeRate-API Open Access (`open.er-api.com/v6/latest`) if Frankfurter fails.
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

### 10.7 LLM (cross-retailer discovery + categorization)

- **Provider:** Google Gemini API. Two models are wired: `gemini-2.5-flash` (`GEMINI_MODEL`) drives categorization (no grounding, structured JSON), and `gemini-2.5-flash-lite` (`GEMINI_SEARCH_MODEL`) drives **all grounded calls** — both search and discovery share the same google_search RPD pool, and Flash's pool is too small (~20/day free tier) for a real search UX.
- **Use cases in V1:**
  1. **Free-text product search** (§5.2 U-ADD-0) — one Gemini call per user-submitted search query, Search-grounded, returns up to 8 candidate listings. Results are cached by normalized query for 24h (`search_cache`, §8.7) so repeated queries do not re-burn quota. When the user picks a search result and clicks **Track**, the remaining supported candidates are passed inline as `discovery_seed` and discovery skips its own LLM call.
  2. **Cross-retailer discovery** (§7.3) — one call per product creation, Search-grounded, returns up to 8 candidate URLs. Skipped entirely when a `discovery_seed` is supplied (search-originated adds).
  3. **Categorization + title cleanup** (§7.7) — one call per product creation when the user leaves the Add modal's category dropdown on "Auto". Plain Gemini call, no Search grounding, structured JSON returning **both** `category` (one of the 5 fixed slugs) and `clean_title` (a short, human-friendly product name, 4–80 chars). Title cleanup piggy-backs on this single request — it does not add a second Gemini call.
- **Free-tier guardrails:** prompts are bounded; search and discovery candidates are capped at 8; categorization is wrapped in a 1.5s hard timeout; grounded search uses a 20s server timeout (`GEMINI_SEARCH_TIMEOUT_S`, Flash-Lite responds in ~1-2s), grounded discovery uses 30s (`GEMINI_DISCOVER_TIMEOUT_S`); search responses are cached server-side for 24h; transient `500/502/503/504` errors retry up to 3 attempts with backoff, while `429` (daily quota cap) **never** retries on either tier — it surfaces immediately as HTTP 429 with a "daily limit" message and the frontend falls back to "Add by URL"; if quota or the API itself is exhausted, all flows fall back gracefully (search: 429/503 with friendly copy + URL fallback; discovery: skip + notify user; categorization: heuristic).
- **Pluggable interface:** a single `LlmProvider` abstraction handles search, discovery, and categorization so we can swap LLMs later without rewriting any pipeline. Each use case is a separate method on the same interface. A `FixtureLlmProvider` is used automatically when `SCRAPER_MODE=fixtures` and no `GEMINI_API_KEY` is set, returning canned JSON from `backend/test/fixtures/search/*.json` so local dev and CI never hit the live Gemini API.
- **Grounded JSON parsing:** Google Search grounding cannot be combined with controlled `response_schema` output on any Flash-family model — search and discovery prompt for JSON in plain text and validate locally (categorization still uses structured output). Natural-language refusals from the grounded model (e.g. "I'm sorry, I can't…" on overly broad queries) are treated as empty results, not malformed responses, so the UI degrades to the empty state + URL fallback instead of an error.
- **Operational visibility:** `GET /health/llm` (unauthenticated) reports `configured`, both model names, both timeouts, and `scraper_mode` without calling Gemini — safe to curl from anywhere when triaging search behavior.

### 10.8 Secrets & environment

Copy `backend/.env.example` → `backend/.env` and `frontend/.env.example` → `frontend/.env` for local development. Variable names and production guidance live in `backend/.env.example`, `backend/core/settings.py`, and `docs/DEPLOYMENT.md` (production URLs, required vs optional vars, GitHub Actions secrets).

Local defaults: `AUTH_BYPASS_ENABLED=true`, `SCRAPER_MODE=fixtures`. Production: `AUTH_BYPASS_ENABLED=false`, `SCRAPER_MODE=live`, plus `WORKER_TOKEN`, `CORS_ALLOWED_ORIGINS`, and provider keys per `docs/DEPLOYMENT.md`. `RESEND_API_KEY` is required on Render for digest sends (H4/T3.6); local/CI tests mock Resend when unset.

GitHub Actions secrets: `WORKER_TOKEN`, `BACKEND_BASE_URL`. CI sets `SCRAPER_MODE=fixtures` and must not require retailer network access.

### 10.9 Development load assumptions

V1 is designed to remain free even while multiple engineers and AI agents iterate. Working assumption: **manual job triggering up to ~30 times per day across parallel agents during heavy development**, plus normal once-daily scheduled runs and ad-hoc adds.

Free-tier headroom check at that load:


| Provider                      | Free tier                            | ~30×/day budget                                                              | Verdict                                                                                                                                                                    |
| ----------------------------- | ------------------------------------ | ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GitHub Actions (private repo) | 2,000 min/mo included                | 30 runs × ~3 min × 30 days ≈ 2,700 min worst case                            | ⚠️ Tight at sustained ceiling. Workflows target ≤ 3 min and use job-level timeouts. If we exceed the monthly cap, move repo to public (unlimited minutes). Tracked in §13. |
| Render web service            | 750 hrs/mo                           | Each wake ≈ 5 min ≪ 750 hrs                                                  | ✅                                                                                                                                                                          |
| Supabase (DB / Auth)          | 500 MB DB, 50k MAU                   | Trivial volume in V1                                                         | ✅                                                                                                                                                                          |
| Gemini Flash (categorization)     | ~1,500 RPD free-tier ceiling | 1 categorization call per *add*. 100 adds/day = 100 calls    | ✅ ~15× headroom over a heavy add day. Categorization is the only non-grounded path. |
| Gemini Flash-Lite (search + discovery grounding) | ~1,000 grounded queries/day free-tier ceiling (separate pool from Flash) | 1 grounded call per *user search* + 1 per non-seeded *add*; search cached 24h server-side | ✅ Cache + `discovery_seed` keep typical day well under 100 calls. **Note:** `gemini-2.5-flash` + `google_search` is capped at ~20 RPD on free tier — using Lite for grounded paths is mandatory until paid tier. |
| Resend                        | 100 emails/day, 3,000/mo             | At most 1 digest/user/day                                                    | ✅                                                                                                                                                                          |
| Frankfurter                   | Unlimited, no key                    | 1 cached call/day                                                            | ✅                                                                                                                                                                          |
| Vercel                        | Generous static + edge               | Negligible                                                                   | ✅                                                                                                                                                                          |


**The risk that's not about provider quotas:** retailers with aggressive bot protection (Nike, Best Buy, Amazon, Foot Locker, Sport Chek) can rate-limit or ban our server IP if engineers iterate against live URLs. The fix is §10.10 (fixture mode), which is a hard V1 deliverable.

**Concurrency safety:** the `/internal/jobs/scrape-all` endpoint takes a Postgres advisory lock so two parallel agents triggering the worker on the same minute don't double-scrape every listing or duplicate `price_history` rows.

### 10.10 Retailer fixture / mock mode

V1 must ship with a lightweight harness that lets engineers and AI agents iterate on scraper, categorization, discovery, notification, and UI code **without making real outbound requests to retailer sites**. 

**Mode switch:**

- Environment variable `SCRAPER_MODE` ∈ `live` | `fixtures` | `record`.
  - `live` (default in production): scrapers hit real retailer URLs.
  - `fixtures` (default in local dev and CI): scrapers read from `backend/test/fixtures/retailers/<retailer_slug>/<fixture_name>.html` (or `.json` for API responses) and parse them through the normal extraction pipeline. No outbound network calls.
  - `record`: same as `live`, but every successful scrape is written to `backend/test/fixtures/retailers/<slug>/...` for future replay. Used sparingly, only when manually capturing a new fixture.

**Fixture coverage requirement:**

- Every supported retailer (§11) ships with at least one in-stock, one out-of-stock, and one multi-variant fixture.
- The generic scraper ships with three fixtures: a JSON-LD-friendly site, an OG-only site, and a site that yields nothing extractable.
- Fixtures are stored alongside the scraper module so adding a retailer always includes its fixtures in the same PR.

**Drift detection:**

- **Status (2026-06-14):** Local tooling shipped (ROADMAP T5.5). Not scheduled in GitHub Actions — run manually when checking scraper health.
- `make check-retailer-drift` (requires `SCRAPER_MODE=live`) scrapes each retailer's canonical product URL and compares a structural fingerprint to committed baselines in `backend/scrapers/drift/snapshots/`.
- Optional `--file-issues` opens/updates/closes GitHub issues tagged `retailer-drift` (one per retailer; requires `GITHUB_TOKEN` + `GITHUB_REPOSITORY`).
- `make update-drift-snapshots` regenerates baselines from fixtures after fixture edits.
- CI (`.github/workflows/ci.yml`) always runs scrapers in `fixtures` mode so PRs never hit live retailers. PRs that change fixtures must update drift baselines in the same commit (`test_drift_snapshots_match_fixtures`).

**Why this is V1, not nice-to-have:**

- Without fixtures, every iteration cycle burns retailer bot-protection budget.
- Without drift detection, the daily scrape can silently degrade and the team only finds out when users complain.
- Both pieces are small (one shared `FixtureLoader`, one workflow, one make target) and unblock all downstream development.

---

## 11. Supported Retailers (V1)

Each natively supported retailer needs a scraper module exposing a `scrape(url) -> ProductSnapshot` function and metadata describing its default extraction strategy and fallback order.


| Slug            | Domain(s)                       | Default category | Notes                                                                                                                                                                |
| --------------- | ------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `amazon_ca`     | amazon.ca                       | other            | Shipped T5.4 — 1P seller verification; twister variants via `curl_cffi` HTML parser.                                                                                |
| `bestbuy_ca`    | bestbuy.ca                      | tech             | Cloudflare-protected; benchmark structured data / `curl_cffi` before Playwright.                                                                                     |
| `apple_ca`      | apple.com/ca                    | tech             | Buy-flow JSON-LD + config grid; shared structured scraper (T5.3).                                                                                                    |
| `nike_ca`       | nike.com/ca                     | shoes            | Shipped T5.4 — `__NEXT_DATA__` parser via `curl_cffi`; HTTP-only (no production Playwright).                                                                         |
| `sportchek`     | sportchek.ca                    | clothing         | Deferred T5.4 — Akamai shell HTML without extractable product data over HTTP-only.                                                                                   |
| `indigo`        | indigo.ca                       | other            | Shopify + ProductGroup format stock; shared structured scraper (T5.3).                                                                                              |
| `canadiantire`  | canadiantire.ca                 | home             | Region-aware (asks for store); use the central/online price.                                                                                                         |
| `costco_ca`     | costco.ca                       | other            | Some pages behind member login — we restrict to public listings only.                                                                                                |
| `abercrombie`   | abercrombie.com (Canada region) | clothing         | Embedded productPrices + scoped SKU inventory; shared structured scraper (T5.3).                                                                                    |
| `oakley`        | oakley.com/en-ca                | other            |                                                                                                                                                                      |
| `footlocker_ca` | footlocker.ca                   | shoes            | Deferred T5.4 — JS-heavy PDP without extractable price over HTTP-only.                                                                                              |
| `vans_ca`       | vans.ca                         | shoes            |                                                                                                                                                                      |
| `palmisleskate` | palmisleskateshop.com           | other            | Small Shopify store; shared Shopify scraper (T5.2).                                                                                                                    |
| `tikiroomskate` | tikiroomskateboards.com         | other            | Small Shopify store; shared Shopify scraper (T5.2).                                                                                                                    |
| `eatyourwater`  | eatyourwater.com                | clothing         | Deferred post-MVP (active store is `.com.au` / AUD-only).                                                                                                            |
| `generic`       | (any other domain)              | `other`          | Best-effort structured data / OG with lightweight HTTP only; no Playwright.                                                                                          |


**Per-retailer scraper checklist (engineering contract):** title, brand (best-effort), image URL, current price in CAD cents, in-stock boolean, list of available variant attribute combinations, and the selected variant attributes for the input URL (when inferable from URL or page state). Each retailer also ships with the fixture coverage required by §10.10.

**Engineering note on scraper reliability:** several of the above retailers run aggressive bot protection. Do not assume Playwright is required until the benchmark harness proves it; try structured data and `curl_cffi` first, then use Playwright as the measured fallback. Expect periodic breakage when sites change. V1 accepts this brittleness as a known limitation; see §13.

---

## 12. Non-Functional Requirements

- **Performance:** product list page loads in < 2s with up to 200 products. Manual refresh of one product should complete in < 30s for non-Playwright retailers; Playwright-backed retailers may be slower because browser cold start dominates.
- **Perceived performance:** every user action surfaces visible feedback within 100ms. All mutations (add, archive, re-categorize, accept/reject discovered match, mark-read) render optimistically and only roll back on server error. Archive confirms with a success toast without leaving the current route (§5.8 U-ARC-1). After add, the product detail category field (and matching dashboard row) show a brief sorting shimmer for at least ~2.5s before revealing the server-resolved category (§7.7); the Add modal stays open with an inline spinner until the add request completes.
- **Design quality:** dashboard and product detail routes target **Lighthouse Performance ≥ 95** and **Accessibility ≥ 95** on a desktop run with throttled CPU. Visual style follows §10.1 design principles.
- **Reliability:** daily scrape job retries each listing up to 2 times with exponential backoff. A run is considered successful if at least 80% of listings scrape successfully.
- **Cost:** $0/month for V1 even while engineers iterate at ~30 manual job triggers/day across parallel agents (see §10.9). All providers used in the core product (Supabase, Vercel, Render, GitHub Actions, Gemini, Resend, Frankfurter) have free tiers that accommodate that load. The core plan excludes hosted scraping APIs such as Firecrawl because one-time credits or paid monthly quotas are incompatible with indefinite free operation.
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


| Risk / limitation                                                    | Impact                                                                                   | V1 mitigation                                                                                                                                                                                                                           |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Scrapers break when retailer HTML changes                            | Listings stop refreshing                                                                 | `scrape_failing` notification after 3 consecutive failures; structured logs; per-retailer scraper is a small isolated module                                                                                                            |
| Bot-protected retailers (Nike, Amazon, Best Buy) block server IPs    | Some listings refresh inconsistently                                                     | Benchmark structured data, `curl_cffi`, and Playwright per retailer; accept best-effort, mark failures clearly to user                                                                                                                  |
| Gemini free tier rate-limited or quota exhausted                     | Discovery silently fails; categorization falls back to heuristic                         | Single `LlmProvider` interface (§10.7); discovery is one-shot per product, categorization has a 1.5s hard timeout and heuristic fallback (§7.7)                                                                                         |
| Gemini model names / free-tier limits change                         | Implementation docs become stale                                                         | Select the current Flash-family free-tier model at implementation time and keep all LLM flows behind `LlmProvider` (§10.7)                                                                                          |
| Gemini 2.5 rejects structured output + Search grounding together     | `/api/search` or discovery returns 502 provider error in production                      | Grounded calls prompt for JSON and parse locally; categorization keeps `response_schema` (§10.7)                                                                                                                   |
| Grounded search exceeds server timeout                               | `/api/search` returns 504 "Search took too long" after loading UX                        | Default `GEMINI_SEARCH_TIMEOUT_S` aligned with discovery (`30.0`); `SearchThinking` covers in-flight wait; 24h `search_cache` avoids repeat Gemini calls                                                          |
| Render free tier cold-starts (15-min idle sleep)                     | First post-idle backend request is slow (~30s) and undermines the "snappy" frontend feel | Acceptable for V1 backend; frontend hosted on Vercel edge so first paint is instant; TanStack Query stale-while-revalidate keeps the dashboard usable while the backend warms; manual refresh users see a skeleton on the affected card |
| Single-region (Canada) hardcoded assumption                          | Non-Canadian friend can't really use it                                                  | V1 explicitly Canada-only; document in onboarding                                                                                                                                                                                       |
| Variant inference is fragile across diverse retailer URL patterns    | Users will see "Needs input" more often than ideal                                       | Explicit "Needs input" UX; not a crash                                                                                                                                                                                                  |
| Currency switcher could mislead user if FX rates are stale           | User sees a price they can't actually pay in that currency                               | 24h cache is acceptable for cosmetic display; thresholds are always CAD                                                                                                                                                                 |
| Amazon 1P-only rule is hard to verify programmatically               | Could accidentally track a 3P seller                                                     | Scraper requires literal "Sold by Amazon.ca" string; otherwise reject with friendly error                                                                                                                                               |
| Email digest could land in spam                                      | User misses sale alerts                                                                  | In-app notifications are the source of truth; email is convenience layer                                                                                                                                                                |
| GitHub Actions cron is best-effort (can run late)                    | Daily scrape may shift by minutes                                                        | Acceptable; not a correctness issue                                                                                                                                                                                                     |
| GitHub Actions free minutes differ by repository visibility          | Private repo could eventually consume included minutes                                   | Stay private for V1; flip the repo to public if monthly minute usage approaches the 2,000-min cap (see §10.9 budget)                                                                                                                    |
| AI categorization mislabels a product                                | User sees the wrong bucket on the dashboard                                              | Manual re-categorize from product detail page; manual overrides are sticky (§7.7) and stop future auto runs from undoing them; `category_source='manual'` recorded on the row                                                           |
| Heavy dev iteration burns retailer bot-protection budget             | Scrapers get rate-limited or IP-banned mid-build                                         | `SCRAPER_MODE=fixtures` is the default in local dev and CI (§10.10); live mode is reserved for the daily scheduled job, manual drift checks, and explicit benchmark runs                                                                |
| Two parallel agents trigger `/internal/jobs/scrape-all` concurrently | Double scrapes, duplicated `price_history` rows                                          | Postgres advisory lock around the scrape entrypoint (§10.9)                                                                                                                                                                             |
| Revisit prompts feel naggy or robotic                                | User disables them or stops trusting the digest                                          | 30-day per-product debounce; settings toggles to disable each prompt type independently; copy guidelines in §7.10 enforced in design review                                                                                             |
| Retailer page structure changes silently                             | Scraped fields drift without anyone noticing                                             | Local drift tooling (`make check-retailer-drift`) compares live scrapes to committed baselines when run manually (§10.10)                                                                                                                                                     |
| ToS / scraping ethics                                                | Long-term legal exposure if app grows                                                    | V1 is personal-use; revisit before any public launch                                                                                                                                                                                    |


---

## 14. Out of Scope / Future Work (V2 candidates)

Captured here so they aren't lost.

- **Cross-retailer "cheaper elsewhere" indicator** (requires reliable matching at scale).
- **Keyboard shortcuts / command palette** (e.g., ⌘K to add, `/` to filter) — explicitly deferred in V1 to keep scope tight.
- **System-theme auto-detection** alongside the existing light/dark toggle.
- **AI categorization with confidence + user confirm** (suggest with score; only auto-apply when score ≥ threshold).
- **Self-recording fixtures** that capture real scrape responses automatically when a retailer changes shape.
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

1. A user can sign in with Google, paste a URL from any of the 16 supported retailers (or any other site), and have it appear in their list within 10 seconds with a current price and an auto-assigned category.
2. AI categorization places ≥ 80% of a 20-product manual-review sample into the bucket a human would have picked. Heuristic fallback runs when the LLM is unavailable.
3. The scraper benchmark harness has been run against representative URLs for every supported retailer and records the selected default strategy plus fallback order.
4. The daily scrape runs on schedule for 7 consecutive days with ≥ 80% per-listing success rate across the user's products.
5. Cross-retailer discovery finds at least one additional listing for at least 60% of products that exist at multiple supported retailers (acknowledging some products genuinely only exist at one).
6. A user receives a daily digest email containing accurate price-drop, back-in-stock, and revisit-prompt events when those events occur.
7. Revisit prompts fire per §7.10 logic in a dry-run unit test against a synthetic 90-day product/price-history fixture, and never repeat within the 30-day debounce window.
8. The 30-day trend chip is visibly correct for products with ≥ 7 days of data.
9. The display-currency control in `/settings` correctly converts and renders for CAD/USD/EUR/GBP.
10. A user can archive, restore, delete, and re-categorize products.
11. A user can toggle between light and dark theme from `/settings`; the preference survives reload.
12. The dashboard and product detail pages hit Lighthouse Performance ≥ 95 and Accessibility ≥ 95 on a desktop throttled run.
13. `SCRAPER_MODE=fixtures` lets engineers run the full backend test suite and a local dev session end-to-end with zero outbound requests to retailer domains. Local drift tooling (`make check-retailer-drift`) compares live scrapes to committed baselines when run manually with `SCRAPER_MODE=live`.
14. A user can delete their account from `/settings` and verify (via Supabase dashboard or integration test) that their data is gone. Production disposable-user smoke verified in T6.2 (`smoke_delete_account.py --live --confirm`).

---

## 16. Open Questions (deferred — to revisit before V2)

These are deliberate trade-offs in V1, written down so the next planning round can revisit them with usage data:

- Should retailer config move from code to DB once we exceed ~20 supported retailers?
- Is one-shot discovery good enough, or do users want a "find more retailers" button on existing products?
- Is a 1-hour manual-refresh cooldown the right balance, or do power users need 5 minutes?
- Should "Needs review" matches expire automatically after N days if untouched?
- Is the 3% trend deadband the right value, or should it scale with product price?
- Do we need a shared, anonymized cross-user price history (de-duplicated by URL) so new users get instant trend data?
- Should the `revisit_on_sale` threshold (default 15% off) scale with item price (e.g., 5% off a $1,000 item is meaningful, 15% off a $20 item isn't)?
- Should AI categorization run in a "confidence + suggest" mode (asks user to confirm if score < threshold) instead of always auto-applying?
- Should the drift-detection workflow auto-disable a retailer's scraper after N consecutive drift failures, or only ever open an issue?

---

*End of V1 PRD.*