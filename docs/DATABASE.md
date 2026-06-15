# Database Specification

Schema and security conventions for **shopping-monitor** (Supabase PostgreSQL).

## Overview

The app uses **Supabase PostgreSQL** with Supabase Auth. Document every table here as you add migrations under `backend/db/migrations/`.

```
┌─────────────────┐
│   auth.users    │  (Supabase managed)
│  (Supabase)     │
└────────┬────────┘
         │
    ┌────┴────┬──────────────┬─────────────────┐
    │         │              │                 │
profiles  products  notifications      fx_rates_cache    search_cache
              │
         product_listings
              │
         price_history
```

---

## Tables

### `profiles`

**RLS:** Pattern A — users select/insert/update/delete their own row.

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

### `products`

**RLS:** Pattern A — users access only rows where `user_id = auth.uid()`. Index on `(user_id, status)`.

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

### `product_listings`

**RLS:** Pattern A via join on `products.user_id`.

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
| `scrape_status`            | `text`         | nullable until first scrape; then `ok`, `failing`, `blocked` |
| `scrape_failure_count`     | `int`          | default 0                                            |
| `created_at`, `updated_at` | `timestamptz`  |                                                      |

### `price_history`

**RLS:** Pattern A via join through `product_listings` → `products.user_id`.

| Column        | Type           | Notes                        |
| ------------- | -------------- | ---------------------------- |
| `id`          | `bigserial` PK |                              |
| `listing_id`  | `uuid`         | FK product_listings, indexed |
| `price_cents` | `int`          | CAD cents, NOT NULL          |
| `is_in_stock` | `bool`         |                              |
| `observed_at` | `timestamptz`  | indexed                      |
| `source`      | `text`         | `scheduled`, `manual`        |

### `notifications`

**RLS:** Pattern A — users access only rows where `user_id = auth.uid()`.

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

### `fx_rates_cache`

**RLS:** Pattern B — service-role only; RLS enabled with no authenticated policies.

| Column       | Type                         |
| ------------ | ---------------------------- |
| `pair`       | `text` PK (e.g. `'CAD_USD'`) |
| `rate`       | `numeric`                    |
| `fetched_at` | `timestamptz`                |

### `search_cache`

**RLS:** Pattern B — service-role only; RLS enabled with no authenticated policies. Cache is intentionally global (not per-user) because product search queries are not PII; the same normalized query from any user reuses the same cached payload.

| Column           | Type          | Notes                                                                                  |
| ---------------- | ------------- | -------------------------------------------------------------------------------------- |
| `query_hash`     | `text` PK     | SHA-256 of `normalize_query(query)` (lowercased, whitespace-collapsed)                 |
| `query`          | `text`        | Original normalized query (kept for diagnostics)                                       |
| `result_payload` | `jsonb`       | Serialized `LlmSearchResult` plus classification metadata                              |
| `fetched_at`     | `timestamptz` | Insert/refresh time; expired after `SEARCH_CACHE_TTL_HOURS` (default 24h). Indexed `DESC`. |

---

## Row Level Security (RLS)

**Every new table in `public` must enable RLS in the same migration** (or an immediately applied follow-up). Never ship tables without RLS.

### Pattern A: User-owned data (client + API)

```sql
ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own rows"
    ON my_table FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own rows"
    ON my_table FOR UPDATE
    USING (auth.uid() = user_id);
```

**Note:** UPDATE requires a SELECT policy in Postgres RLS or updates silently affect 0 rows.

### Pattern B: Backend-only (service role)

```sql
ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;
-- No policies for authenticated / anon — PostgREST denies direct client access.
-- FastAPI uses SUPABASE_SERVICE_ROLE_KEY for server-side queries.
```

Use Pattern B when all reads/writes go through the API and the browser must not query the table directly.

### Supabase schema checklist

Before opening a PR that adds or changes Supabase schema:

1. Enable RLS on every new `public` table in the same migration.
2. Choose the narrowest access model:
   - Pattern A for user-owned rows the browser/API may read by user.
   - Pattern B for backend-only tables such as caches, job state, advisory-lock helpers, or operational metadata.
3. Never use `user_metadata` for authorization decisions. Use `auth.uid()`, app-owned tables, or trusted `app_metadata` only when necessary.
4. Keep `SUPABASE_SERVICE_ROLE_KEY` server-only; frontend code may only use the publishable/anon key.
5. Add indexes for every expected ownership join and high-volume filter (`user_id`, `product_id`, `listing_id`, status fields, and timestamp windows).
6. Use `TIMESTAMPTZ` for timestamps and integer cents for money.
7. If creating views in an exposed schema, use `security_invoker = true` where supported or keep the view out of exposed schemas.
8. Update this document's table list and migration list in the same change.

---

## Extending the Schema

When adding features:

1. **New tables** should reference `auth.users(id)` or a `profiles` table for ownership.
2. **Always enable RLS** (see patterns above).
3. **Use TIMESTAMPTZ** for all timestamp columns.
4. **Add indexes** for frequently queried columns.
5. **Document** all new tables and columns in this file.
6. **Create migrations** in `backend/db/migrations/` with sequential `NNN_snake_case.sql` names.
7. **Reference each migration filename** in this doc (required by `scripts/check_migrations.py` in CI).

### Test data (integration tests)

When integration tests need DB access:

- Use dedicated `test_*` tables or isolated rows with a run-specific prefix.
- Tear down only data created by the test (avoid deleting shared CI fixtures).
- Mark tests with `@pytest.mark.integration`.

---

## Migrations

| File | Description |
|------|-------------|
| `001_core_schema.sql` | Initial core schema (profiles, products, product_listings, price_history, notifications, fx_rates_cache) with RLS, indexes, and updated_at trigger |
| `002_scrape_job_advisory_lock.sql` | Pattern B advisory-lock helpers (`try_acquire_scrape_all_lock`, `release_scrape_all_lock`) for T3.5 scheduled scrape-all job deduplication |
| `003_search_cache.sql` | Pattern B `search_cache` table for the search-based product add flow (T8.1) — global 24h cache keyed by SHA-256 of the normalized query |

**Apply on the linked Supabase project:** Supabase MCP `apply_migration`, or `python scripts/apply_supabase_migration.py <filename>` (see `AGENTS.md` § Applying Supabase migrations). CI only validates migration files exist and are documented here.

### Advisory lock helpers (Pattern B)

**RLS:** No table — `SECURITY DEFINER` functions callable only via service role (`client.rpc(...)`).

| Function | Returns | Notes |
| -------- | ------- | ----- |
| `try_acquire_scrape_all_lock()` | `boolean` | `pg_try_advisory_lock(8675309)`; false when another scrape-all run holds the lock |
| `release_scrape_all_lock()` | `boolean` | `pg_advisory_unlock(8675309)`; called in `finally` after scrape-all completes |

Python constant `SCRAPE_ALL_ADVISORY_LOCK_KEY = 8675309` in `backend/services/scrape_job_service.py` must stay in sync with the SQL key.
