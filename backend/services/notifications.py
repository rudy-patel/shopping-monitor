"""Notification evaluation interfaces (PRD §7.5, §7.10)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, field_validator

from services.pricing import (
    PRICE_DROP_DEBOUNCE_HOURS,
    REVISIT_DEBOUNCE_DAYS,
    REVISIT_PRICE_DROP_OVERLAP_DAYS,
    ListingDailyObservation,
    baseline_max_daily_minimum,
    current_daily_minimum,
    is_revisit_on_sale_eligible,
    product_daily_minimum,
    should_fire_price_drop,
)

_PAYLOAD_MAX_BYTES = 8 * 1024
REVISIT_MIN_PRODUCT_AGE_DAYS = 30


class NotificationKind(str, Enum):
    PRICE_DROP = "price_drop"
    BACK_IN_STOCK = "back_in_stock"
    DISCOVERY_COMPLETE = "discovery_complete"
    NEEDS_INPUT = "needs_input"
    SCRAPE_FAILING = "scrape_failing"
    REVISIT_ON_SALE = "revisit_on_sale"
    REVISIT_STALE = "revisit_stale"


class NotificationProposal(BaseModel):
    user_id: UUID
    product_id: UUID | None = None
    listing_id: UUID | None = None
    type: NotificationKind
    payload: dict[str, Any] = {}

    @field_validator("payload")
    @classmethod
    def validate_payload_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        serialized = json.dumps(value, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > _PAYLOAD_MAX_BYTES:
            raise ValueError(
                f"payload serialized size exceeds {_PAYLOAD_MAX_BYTES} bytes"
            )
        return value


class ProfileNotificationFlags(BaseModel):
    notifications_enabled: bool
    default_threshold_pct: int
    revisit_prompts_enabled: bool
    revisit_on_sale_enabled: bool
    revisit_stale_enabled: bool
    revisit_stale_days: int


class ProductNotificationSnapshot(BaseModel):
    status: str
    notifications_enabled: bool
    notification_threshold_pct: int | None
    created_at: datetime
    last_user_interaction_at: datetime | None


class ListingNotificationSnapshot(BaseModel):
    id: UUID
    retailer_slug: str
    is_in_stock: bool | None
    previous_is_in_stock: bool | None
    scrape_failure_count: int
    review_status: str
    is_primary: bool


class RecentNotificationRow(BaseModel):
    type: str
    product_id: UUID | None = None
    listing_id: UUID | None = None
    created_at: datetime


class NotificationEvaluationContext(BaseModel):
    user_id: UUID
    product_id: UUID
    evaluated_at: datetime
    scrape_source: Literal["scheduled", "manual"]
    effective_threshold_pct: int
    profile: ProfileNotificationFlags
    product: ProductNotificationSnapshot
    listings: list[ListingNotificationSnapshot] = []
    recent_observations: list[ListingDailyObservation] = []
    recent_notifications: list[RecentNotificationRow] = []

    @field_validator("evaluated_at")
    @classmethod
    def validate_evaluated_at_tz_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluated_at must be timezone-aware")
        return value


class NotificationEvaluator(Protocol):
    kind: NotificationKind

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        ...


def notifications_enabled(
    profile: ProfileNotificationFlags,
    product: ProductNotificationSnapshot,
) -> bool:
    return profile.notifications_enabled and product.notifications_enabled


def has_recent_notification(
    recent: Sequence[RecentNotificationRow],
    *,
    kind: NotificationKind | str,
    product_id: UUID | None = None,
    listing_id: UUID | None = None,
    within_hours: int | None = None,
    within_days: int | None = None,
    evaluated_at: datetime,
) -> bool:
    kind_value = kind.value if isinstance(kind, NotificationKind) else kind
    if within_hours is not None:
        cutoff = evaluated_at - timedelta(hours=within_hours)
    elif within_days is not None:
        cutoff = evaluated_at - timedelta(days=within_days)
    else:
        raise ValueError("within_hours or within_days is required")

    for row in recent:
        if row.type != kind_value:
            continue
        if product_id is not None and row.product_id != product_id:
            continue
        if listing_id is not None and row.listing_id != listing_id:
            continue
        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if created_at >= cutoff:
            return True
    return False


def _has_revisit_debounce(ctx: NotificationEvaluationContext) -> bool:
    for kind in (NotificationKind.REVISIT_ON_SALE, NotificationKind.REVISIT_STALE):
        if has_recent_notification(
            ctx.recent_notifications,
            kind=kind,
            product_id=ctx.product_id,
            within_days=REVISIT_DEBOUNCE_DAYS,
            evaluated_at=ctx.evaluated_at,
        ):
            return True
    return False


def _product_age_days(ctx: NotificationEvaluationContext) -> int:
    created_at = ctx.product.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return (ctx.evaluated_at - created_at).days


def _interaction_age_days(ctx: NotificationEvaluationContext) -> int | None:
    last = ctx.product.last_user_interaction_at
    if last is None:
        return None
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    return (ctx.evaluated_at - last).days


def _revisit_on_sale_eligible(ctx: NotificationEvaluationContext) -> bool:
    if not notifications_enabled(ctx.profile, ctx.product):
        return False
    if not ctx.profile.revisit_prompts_enabled or not ctx.profile.revisit_on_sale_enabled:
        return False
    if ctx.product.status != "active":
        return False
    if _product_age_days(ctx) < REVISIT_MIN_PRODUCT_AGE_DAYS:
        return False
    today = ctx.evaluated_at.date()
    if today not in product_daily_minimum(ctx.recent_observations):
        return False
    baseline = baseline_max_daily_minimum(ctx.recent_observations, today=today)
    current = current_daily_minimum(ctx.recent_observations, today=today)
    if baseline is None or current is None:
        return False
    if not is_revisit_on_sale_eligible(baseline_cents=baseline, current_cents=current):
        return False
    if has_recent_notification(
        ctx.recent_notifications,
        kind=NotificationKind.PRICE_DROP,
        product_id=ctx.product_id,
        within_days=REVISIT_PRICE_DROP_OVERLAP_DAYS,
        evaluated_at=ctx.evaluated_at,
    ):
        return False
    return True


class PriceDropEvaluator:
    kind = NotificationKind.PRICE_DROP

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        if not notifications_enabled(ctx.profile, ctx.product):
            return []
        if ctx.product.status != "active":
            return []
        today = ctx.evaluated_at.date()
        baseline = baseline_max_daily_minimum(ctx.recent_observations, today=today)
        current = current_daily_minimum(ctx.recent_observations, today=today)
        if baseline is None or current is None:
            return []
        if not should_fire_price_drop(
            baseline_cents=baseline,
            current_cents=current,
            threshold_pct=ctx.effective_threshold_pct,
        ):
            return []
        if has_recent_notification(
            ctx.recent_notifications,
            kind=NotificationKind.PRICE_DROP,
            product_id=ctx.product_id,
            within_hours=PRICE_DROP_DEBOUNCE_HOURS,
            evaluated_at=ctx.evaluated_at,
        ):
            return []
        return [
            NotificationProposal(
                user_id=ctx.user_id,
                product_id=ctx.product_id,
                type=NotificationKind.PRICE_DROP,
                payload={
                    "old_price_cents": baseline,
                    "new_price_cents": current,
                },
            )
        ]


class BackInStockEvaluator:
    kind = NotificationKind.BACK_IN_STOCK

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        if not notifications_enabled(ctx.profile, ctx.product):
            return []
        if ctx.product.status != "active":
            return []
        proposals: list[NotificationProposal] = []
        for listing in ctx.listings:
            if listing.previous_is_in_stock is not False or listing.is_in_stock is not True:
                continue
            if has_recent_notification(
                ctx.recent_notifications,
                kind=NotificationKind.BACK_IN_STOCK,
                listing_id=listing.id,
                within_hours=PRICE_DROP_DEBOUNCE_HOURS,
                evaluated_at=ctx.evaluated_at,
            ):
                continue
            proposals.append(
                NotificationProposal(
                    user_id=ctx.user_id,
                    product_id=ctx.product_id,
                    listing_id=listing.id,
                    type=NotificationKind.BACK_IN_STOCK,
                    payload={"retailer_slug": listing.retailer_slug},
                )
            )
        return proposals


class ScrapeFailingEvaluator:
    kind = NotificationKind.SCRAPE_FAILING

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        if not notifications_enabled(ctx.profile, ctx.product):
            return []
        if ctx.scrape_source != "scheduled":
            return []
        proposals: list[NotificationProposal] = []
        for listing in ctx.listings:
            if listing.scrape_failure_count != 3:
                continue
            proposals.append(
                NotificationProposal(
                    user_id=ctx.user_id,
                    product_id=ctx.product_id,
                    listing_id=listing.id,
                    type=NotificationKind.SCRAPE_FAILING,
                    payload={},
                )
            )
        return proposals


class RevisitOnSaleEvaluator:
    kind = NotificationKind.REVISIT_ON_SALE

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        if _has_revisit_debounce(ctx):
            return []
        if not _revisit_on_sale_eligible(ctx):
            return []
        return [
            NotificationProposal(
                user_id=ctx.user_id,
                product_id=ctx.product_id,
                type=NotificationKind.REVISIT_ON_SALE,
                payload={},
            )
        ]


class RevisitStaleEvaluator:
    kind = NotificationKind.REVISIT_STALE

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        if not notifications_enabled(ctx.profile, ctx.product):
            return []
        if not ctx.profile.revisit_prompts_enabled:
            return []
        if not ctx.profile.revisit_stale_enabled:
            return []
        if ctx.product.status != "active":
            return []
        stale_days = ctx.profile.revisit_stale_days
        if _product_age_days(ctx) < stale_days:
            return []
        interaction_age = _interaction_age_days(ctx)
        if interaction_age is not None and interaction_age < stale_days:
            return []
        if _has_revisit_debounce(ctx):
            return []
        if _revisit_on_sale_eligible(ctx):
            return []
        return [
            NotificationProposal(
                user_id=ctx.user_id,
                product_id=ctx.product_id,
                type=NotificationKind.REVISIT_STALE,
                payload={},
            )
        ]


class NullNotificationEvaluator:
    """Hard-off default; evaluate always returns []."""

    kind = NotificationKind.PRICE_DROP

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        return []


class RecordingNotificationEvaluator:
    """Test fake that records context and returns configured proposals."""

    def __init__(
        self,
        proposals: Sequence[NotificationProposal],
        *,
        kind: NotificationKind = NotificationKind.PRICE_DROP,
    ) -> None:
        self.kind = kind
        self._proposals = list(proposals)
        self.received: list[NotificationEvaluationContext] = []

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        self.received.append(ctx)
        return list(self._proposals)


class CompositeNotificationEvaluator:
    """Runs child evaluators sequentially and concatenates results."""

    kind = NotificationKind.PRICE_DROP

    def __init__(self, evaluators: Sequence[NotificationEvaluator]) -> None:
        self._evaluators = list(evaluators)

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        results: list[NotificationProposal] = []
        for evaluator in self._evaluators:
            results.extend(evaluator.evaluate(ctx))
        return results


def default_composite_evaluator() -> CompositeNotificationEvaluator:
    return _DEFAULT_COMPOSITE_EVALUATOR


_DEFAULT_COMPOSITE_EVALUATOR = CompositeNotificationEvaluator(
    [
        PriceDropEvaluator(),
        BackInStockEvaluator(),
        ScrapeFailingEvaluator(),
        RevisitOnSaleEvaluator(),
        RevisitStaleEvaluator(),
    ]
)
