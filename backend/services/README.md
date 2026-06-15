# V1 service interfaces

This package defines the service-interface boundary for Shopping Monitor V1: LLM, categorization, FX, mail, notification evaluation, and pricing/trend helpers. T1.5 ships Protocols, Pydantic I/O types, no-op/fake providers, and pure-function helpers; concrete provider implementations land in later roadmap tasks.

## Scope

| Surface | T1.5 ships | Concrete impl lands in |
| --- | --- | --- |
| `LlmProvider` (discover, categorize) | Protocol + Pydantic I/O types + exceptions + `NoOpLlmProvider` + `FakeLlmProvider` + `GeminiFlashLlmProvider` categorize + discover | — |
| `Categorizer` | Protocol + `DefaultCategorizer` orchestrator + `heuristic_category()` + `get_categorizer()` factory | T2.5 wires into product API |
| `FxService` | Protocol + `StaticFxService` + `CachedFxService` + `FxRate`/`FxRates` types + live providers | T4.1 done |
| `MailService` | Protocol + `NoOpMailService` + `DigestEmail`/`DigestNotificationEntry` models | T3.6 (Resend client + template rendering) |
| Notification evaluators | `NotificationEvaluator` Protocol + five evaluator implementations + orchestrator in `notification_evaluation.py` | T3.5 wires scheduled scrape-all caller |
| Price/trend helpers | Pure-function module with constants, eligibility filter, daily-minimum, baseline/current helpers, trend math, price-drop & revisit-on-sale helpers | Direct callers in T2.5, T3.4, T3.5 |

## Categorizer

```python
from services import CategorizationContext, get_categorizer

result = get_categorizer().categorize(
    CategorizationContext(
        title="Example Laptop",
        retailer_slug="bestbuy_ca",
        breadcrumbs=["Electronics", "Computers"],
    )
)
# result.category, result.source, result.clean_title
```

`get_categorizer()` wires `GeminiFlashLlmProvider` when `GEMINI_API_KEY` is set; otherwise it falls back to `NoOpLlmProvider` and the heuristic waterfall. Heuristic precedence (PRD §7.7): retailer default → breadcrumb keywords → title/brand keywords → `other`.

The same Gemini call also returns a `clean_title` (4-80 chars; otherwise `None`) — a short, human-friendly product name used when it is **strictly shorter** than the scraped title. This adds **zero** Gemini requests per add since both fields ride one structured-JSON response. Heuristic / `default_other` fallbacks intentionally leave `clean_title` as `None` and the scraped title is kept verbatim. The original scraped title is always preserved on `product_listings.scrape_snapshot.title` for traceability.

### Human smoke (H3)

Requires Python 3.12. **Live Gemini calls are opt-in only** — pytest and CI always mock `genai.Client` and clear `GEMINI_API_KEY` (see `backend/test/conftest.py`). Use `--live` for a one-off manual canary after H3 setup:

```bash
cd backend && source venv/bin/activate
python scripts/smoke_gemini_categorize.py                      # dry-run heuristic path
python scripts/smoke_gemini_categorize.py --expect-heuristic   # assert no LLM path
python scripts/smoke_gemini_categorize.py --live               # real Gemini (H3 only)
```

### Human smoke — discovery (H3)

```bash
cd backend && source venv/bin/activate
python scripts/smoke_gemini_discover.py                        # dry-run no-op path
python scripts/smoke_gemini_discover.py --live                 # real Gemini Search-grounded discover (H3 only)
```

## LlmProvider

```python
from services import FakeLlmProvider, GeminiFlashLlmProvider, get_llm_provider, LlmCategorizationResult

llm = get_llm_provider()
# or for tests:
llm = FakeLlmProvider(
    categorize_result=LlmCategorizationResult(category="tech"),
)
```

`GeminiFlashLlmProvider` uses Gemini structured JSON output with a 1.5s categorize timeout (`GEMINI_CATEGORIZE_TIMEOUT_S`) and a 30s discover timeout (`GEMINI_DISCOVER_TIMEOUT_S`). Discover uses Google Search grounding when available. `get_llm_provider()` returns `NoOpLlmProvider` when `GEMINI_API_KEY` is unset.

## Discovery (T3.1)

`run_discovery_for_product(product_id)` runs as a FastAPI `BackgroundTasks` job after `POST /api/products`. It calls `LlmProvider.discover()`, scrapes candidates through the retailer registry, scores matches via `services.matching`, auto-adds or queues needs-review listings, and writes a `discovery_complete` notification only when at least one listing was auto-added or queued.

```python
from uuid import UUID

from services.discovery import run_discovery_for_product

run_discovery_for_product(UUID("..."))
```

Match scoring weights (no image pHash in T3.1): title Jaccard 0.444, brand exact 0.222, variant exact 0.333. Thresholds: auto-add ≥ 0.85, needs-review 0.60–0.849, discard < 0.60. Empty reference variants score 1.0 on the variant term (supports `needs_input` products).

Needs-review rows store a truncated LLM `discovery_justification` in `scrape_snapshot` for the review queue UI (T3.2). Discovery cap counting excludes `rejected` rows so freed slots can accept new candidates.

## Listing review (T3.2)

Authenticated product routes for user-owned listings:

- `POST /api/products/{product_id}/listings/{listing_id}/accept` — `needs_review` → `accepted`
- `POST /api/products/{product_id}/listings/{listing_id}/reject` — `needs_review` → `rejected`
- `DELETE /api/products/{product_id}/listings/{listing_id}` — hard-delete non-primary rows

All three touch `products.last_user_interaction_at` and return refreshed `ProductDetail`. Invalid transitions return 409; wrong owner returns 404.

## Notifications read API (T3.3)

`services/notification_service.py` powers the authenticated notification list and actions:

- `GET /api/notifications` — paginated list (offset/limit, 90-day query filter), global `unread_count`, product title enrichment
- `POST /api/notifications/mark-read` — bulk or per-id mark-read; touches `products.last_user_interaction_at` when `product_id` is set
- `POST /api/notifications/{id}/action` — revisit `keep` / `archive` (archive reuses `update_product(status='archived')`)

Click-to-navigate on non-revisit types marks read before routing. Bell unread count refetches on window focus only (no polling).

## FxService

Production wiring uses `CachedFxService` via `services.factory.get_fx_service()`:

- **Primary provider:** `GET https://api.frankfurter.dev/v1/latest?base=CAD&symbols=USD,EUR,GBP`
- **Fallback provider:** `GET https://open.er-api.com/v6/latest/CAD` (ExchangeRate-API Open Access, keyless)
- **Cache:** `fx_rates_cache` pairs `CAD_USD`, `CAD_EUR`, `CAD_GBP` with 24h TTL (`fx_cache_ttl_hours`)
- **Stale policy:** if both providers fail, serve expired cache with `stale: true`; empty cache → HTTP 503
- **API:** `GET /api/fx/rates` (authenticated) returns decimal-string rates for display conversion only

```python
from decimal import Decimal

from services import StaticFxService

fx = StaticFxService(rates={"USD": Decimal("0.74")})
display = fx.convert_cad_cents(12345, quote="USD")
```

## MailService (T3.6)

Production wiring uses `services.factory.get_mail_service()`:

- **`RESEND_API_KEY` set** → `ResendMailService` (`services/resend_mail.py`)
- **Unset** → `NoOpMailService` (safe default; digest job does not send or mark `email_sent_at`)

Digest copy and deep links live in `services/digest_templates.py` (mirrors `NotificationRow.tsx`; CAD display only). Subject: `Your Shopping Monitor digest`.

```python
from datetime import datetime, timezone
from uuid import uuid4

from services import DigestEmail, DigestNotificationEntry, NoOpMailService, NotificationKind
from services.factory import get_mail_service

mail = get_mail_service()  # NoOp when RESEND_API_KEY unset
mail.send_digest(
    DigestEmail(
        to_email="user@example.com",
        subject="Your Shopping Monitor digest",
        text_body="...",
        html_body="...",
        entries=[
            DigestNotificationEntry(
                notification_id=uuid4(),
                type=NotificationKind.PRICE_DROP,
                product_id=uuid4(),
                product_title="Example",
                summary="Example dropped from $100.00 to $80.00.",
                deep_link="https://app.example.com/products/abc",
                created_at=datetime.now(timezone.utc),
            )
        ],
    )
)
```

**Digest job:** `POST /internal/jobs/send-digests` (worker token) runs `digest_job_service.run_send_digests()`. Selects unread notifications with `email_sent_at IS NULL` within the 90-day window. Skips users with `email_digest_enabled=false` or zero qualifying rows. Resolves recipient via Supabase Auth admin API (`auth.admin.get_user_by_id`), not `profiles`. Marks `email_sent_at` only after a successful Resend send. When `RESEND_API_KEY` is unset, `mail_provider` is `noop` and qualifying users increment `users_skipped_noop` (no sends or marks). `profiles.notifications_enabled` does **not** gate digest delivery (PRD §7.6).

**Worker boundary:** GitHub Actions `.github/workflows/digest.yml` (cron `0 14 * * *` UTC + `workflow_dispatch`) runs `backend/workers/send_digests.py`.

**Manual smoke:** `python scripts/smoke_resend_digest.py` (dry-run default); `--live --to <email>` for one sandbox send (never in CI).

## NotificationEvaluator (T3.4)

Evaluators run in composite order (first match wins for revisit mutual exclusion):

`PriceDrop` → `BackInStock` → `ScrapeFailing` → `RevisitOnSale` → `RevisitStale`

**Global gate:** `profiles.notifications_enabled = false` or `products.notifications_enabled = false` suppresses all five evaluators.

**Payload contracts:**

| Kind | Payload |
| --- | --- |
| `price_drop` | `{ "old_price_cents": int, "new_price_cents": int }` |
| `back_in_stock` | `{ "retailer_slug": str }` |
| `scrape_failing` | `{}` |
| `revisit_on_sale` / `revisit_stale` | `{}` |

**Locked behavior (T3.4):**

- Manual refresh increments `scrape_failure_count` on failure but **`scrape_failing` only fires for `scrape_source="scheduled"`**.
- `scrape_failing` fires once when count reaches **3** (no repeat at 4+; re-fires after success reset → 3 again).
- Revisit evaluators run on manual refresh too (product-scoped).
- `scrape_failing` respects profile `notifications_enabled`; revisit prompts require revisit flags.

```python
from datetime import datetime, timezone
from uuid import UUID

from services.notification_evaluation import run_post_scrape_evaluation

run_post_scrape_evaluation(
    client,
    user_id=UUID("..."),
    product_id=UUID("..."),
    evaluated_at=datetime.now(timezone.utc),
    scrape_source="manual",  # or "scheduled" in T3.5 scrape-all
    listings_before={
        "<listing_id>": {
            "is_in_stock": True,
            "scrape_failure_count": 0,
        }
    },
)
```

**T3.5 scheduled scrape-all:** `POST /internal/jobs/scrape-all` (worker token) runs `scrape_job_service.run_scrape_all()`. Step 6 uses `mode="scrape_triggered"` (price drop, back-in-stock, scrape failing) for products touched in the run; step 7 uses `mode="revisit_only"` per user with active products. Manual refresh keeps `mode="full"`. Scrape-all does **not** update `products.last_refresh_at` or `last_user_interaction_at`.

```python
from services.notification_evaluation import (
    EvaluatorMode,
    evaluator_for_mode,
    run_post_scrape_evaluation,
    run_revisit_evaluation_for_active_products,
)

run_post_scrape_evaluation(..., scrape_source="scheduled", mode="scrape_triggered")
run_revisit_evaluation_for_active_products(client, user_id, evaluated_at, mode="revisit_only")
```

**Worker boundary:** GitHub Actions `.github/workflows/scrape.yml` (cron `0 8 * * *` UTC + `workflow_dispatch`) runs `backend/workers/scrape_all.py`, which POSTs to the deployed backend with `X-Worker-Token`.

## Pricing helpers

```python
from datetime import date

from services import ListingDailyObservation, compute_trend

trend = compute_trend(observations, today=date(2026, 6, 14))
# trend.direction, trend.delta_pct, trend.days_of_data
```

## Event-driven notifications

`discovery_complete` (T3.1) and `needs_input` (T2.5) are **not** evaluator kinds — they are emitted directly by the discovery job and product-add path respectively. Only the five evaluator-backed kinds have implementations in T3.4:

- `PriceDropEvaluator`
- `BackInStockEvaluator`
- `ScrapeFailingEvaluator`
- `RevisitOnSaleEvaluator`
- `RevisitStaleEvaluator`

## Heuristic notes

- Heuristic order: retailer default, then breadcrumb keywords, then title/brand keywords.
- Breadcrumb keywords match whole tokens (e.g. `"laptops"` matches, but `"tops"` does not false-match inside `"laptops"`).
- Title/brand keywords use substring matching; future tasks may tighten this if mislabels show up in live adds.

## Deferred to later tasks

- **T6.4** — Seven-day scrape reliability check after cron enablement (T6.3 done).

## Account deletion (T4.3)

`DELETE /api/account` (authenticated) calls `account_service.delete_account()`:

1. Verify the auth user exists via `auth.admin.get_user_by_id`.
2. Delete via `auth.admin.delete_user` (service-role client).
3. Postgres `ON DELETE CASCADE` from `001_core_schema.sql` removes `profiles`, `products`, `notifications`, and dependent `product_listings` / `price_history`.

**Guards:** Returns **403** when `AUTH_BYPASS_ENABLED=true` (protects the dev bypass user). Protected identities (`00000000-0000-0000-0000-000000000001`, `rutvik@ualberta.ca`) must never be deleted — enforced in `backend/core/protected_accounts.py` (re-exported in `backend/test/disposable_users.py` for tests/smoke).

**Frontend:** Settings **Account** section opens `DeleteAccountDialog`; on success the client signs out and navigates to `/login`.

**Manual smoke:** `python scripts/smoke_delete_account.py` (dry-run default); `--live --confirm` against local Supabase only (never CI or production).
