# V1 service interfaces

This package defines the service-interface boundary for Shopping Monitor V1: LLM, categorization, FX, mail, notification evaluation, and pricing/trend helpers. T1.5 ships Protocols, Pydantic I/O types, no-op/fake providers, and pure-function helpers; concrete provider implementations land in later roadmap tasks.

## Scope

| Surface | T1.5 ships | Concrete impl lands in |
| --- | --- | --- |
| `LlmProvider` (discover, categorize) | Protocol + Pydantic I/O types + exceptions + `NoOpLlmProvider` + `FakeLlmProvider` + `GeminiFlashLlmProvider` categorize + discover | — |
| `Categorizer` | Protocol + `DefaultCategorizer` orchestrator + `heuristic_category()` + `get_categorizer()` factory | T2.5 wires into product API |
| `FxService` | Protocol + `StaticFxService` + `FxRate`/`FxRates` types + `convert_cad_cents()` | T4.1 (Frankfurter primary + exchangerate.host fallback + 24h cache) |
| `MailService` | Protocol + `NoOpMailService` + `DigestEmail`/`DigestNotificationEntry` models | T3.6 (Resend client + template rendering) |
| Notification evaluators | `NotificationEvaluator` Protocol + per-kind stub classes (return `[]`) + `Null`/`Recording`/`Composite` evaluators + `NotificationProposal`/`NotificationEvaluationContext` types | T3.4 fills evaluator bodies |
| Price/trend helpers | Pure-function module with constants, eligibility filter, daily-minimum, trend math, price-drop & revisit-on-sale helpers | Direct callers in T2.5, T3.3, T3.4 |

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
# result.category, result.source
```

`get_categorizer()` wires `GeminiFlashLlmProvider` when `GEMINI_API_KEY` is set; otherwise it falls back to `NoOpLlmProvider` and the heuristic waterfall. Heuristic precedence (PRD §7.7): retailer default → breadcrumb keywords → title/brand keywords → `other`.

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

```python
from decimal import Decimal

from services import StaticFxService

fx = StaticFxService(rates={"USD": Decimal("0.74")})
display = fx.convert_cad_cents(12345, quote="USD")
```

## MailService

```python
from datetime import datetime, timezone
from uuid import uuid4

from services import DigestEmail, DigestNotificationEntry, NoOpMailService, NotificationKind

mail = NoOpMailService()
mail.send_digest(
    DigestEmail(
        to_email="user@example.com",
        subject="Your daily digest",
        text_body="...",
        html_body="...",
        entries=[
            DigestNotificationEntry(
                notification_id=uuid4(),
                type=NotificationKind.PRICE_DROP,
                product_id=uuid4(),
                product_title="Example",
                summary="Price dropped 20%",
                deep_link="https://app.example.com/products/abc",
                created_at=datetime.now(timezone.utc),
            )
        ],
    )
)
assert len(mail.sent) == 1
```

## NotificationEvaluator

```python
from services import (
    BackInStockEvaluator,
    CompositeNotificationEvaluator,
    PriceDropEvaluator,
    RevisitOnSaleEvaluator,
    RevisitStaleEvaluator,
    ScrapeFailingEvaluator,
)

evaluator = CompositeNotificationEvaluator([
    PriceDropEvaluator(),
    BackInStockEvaluator(),
    ScrapeFailingEvaluator(),
    RevisitOnSaleEvaluator(),
    RevisitStaleEvaluator(),
])
proposals = evaluator.evaluate(ctx)
```

## Pricing helpers

```python
from datetime import date

from services import ListingDailyObservation, compute_trend

trend = compute_trend(observations, today=date(2026, 6, 14))
# trend.direction, trend.delta_pct, trend.days_of_data
```

## Event-driven notifications

`discovery_complete` (T3.1) and `needs_input` (T2.5) are **not** evaluator kinds — they are emitted directly by the discovery job and product-add path respectively. Only the five evaluator-backed kinds have stub classes in T1.5:

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

- **T3.4** — Evaluator bodies; tightening `NotificationEvaluationContext` placeholder `dict[str, Any]` fields into typed snapshots.
- **T3.6** — Resend `MailService` + HTML/text digest templates; swap `DigestEmail.to_email` to `EmailStr` once `email-validator` is added.
- **T4.1** — Frankfurter primary + `exchangerate.host` fallback + 24h `fx_rates_cache`.
