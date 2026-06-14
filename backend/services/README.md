# V1 service interfaces

This package defines the service-interface boundary for Shopping Monitor V1: LLM, categorization, FX, mail, notification evaluation, and pricing/trend helpers. T1.5 ships Protocols, Pydantic I/O types, no-op/fake providers, and pure-function helpers; concrete provider implementations land in later roadmap tasks.

## Scope

| Surface | T1.5 ships | Concrete impl lands in |
| --- | --- | --- |
| `LlmProvider` (discover, categorize) | Protocol + Pydantic I/O types + exceptions + `NoOpLlmProvider` + `FakeLlmProvider` | T2.4 categorize, T3.1 discover |
| `Categorizer` | Protocol + `DefaultCategorizer` orchestrator + `heuristic_category()` | T2.4 tunes heuristic + wires real Gemini |
| `FxService` | Protocol + `StaticFxService` + `FxRate`/`FxRates` types + `convert_cad_cents()` | T4.1 (Frankfurter primary + exchangerate.host fallback + 24h cache) |
| `MailService` | Protocol + `NoOpMailService` + `DigestEmail`/`DigestNotificationEntry` models | T3.6 (Resend client + template rendering) |
| Notification evaluators | `NotificationEvaluator` Protocol + per-kind stub classes (return `[]`) + `Null`/`Recording`/`Composite` evaluators + `NotificationProposal`/`NotificationEvaluationContext` types | T3.4 fills evaluator bodies |
| Price/trend helpers | Pure-function module with constants, eligibility filter, daily-minimum, trend math, price-drop & revisit-on-sale helpers | Direct callers in T2.5, T3.3, T3.4 |

## Categorizer

```python
from services import CategorizationContext, DefaultCategorizer, NoOpLlmProvider

result = DefaultCategorizer(NoOpLlmProvider()).categorize(
    CategorizationContext(
        title="Example Laptop",
        retailer_slug="bestbuy_ca",
        breadcrumbs=["Electronics", "Computers"],
    )
)
# result.category, result.source
```

## LlmProvider

```python
from services import FakeLlmProvider, LlmCategorizationResult

llm = FakeLlmProvider(
    categorize_result=LlmCategorizationResult(category="tech"),
)
```

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

## Deferred to later tasks

- **T2.4** — Gemini Flash `LlmProvider` categorize implementation; heuristic keyword expansion.
- **T3.1** — Gemini Flash `LlmProvider` discover implementation.
- **T3.4** — Evaluator bodies; tightening `NotificationEvaluationContext` placeholder `dict[str, Any]` fields into typed snapshots.
- **T3.6** — Resend `MailService` + HTML/text digest templates; swap `DigestEmail.to_email` to `EmailStr` once `email-validator` is added.
- **T4.1** — Frankfurter primary + `exchangerate.host` fallback + 24h `fx_rates_cache`.
