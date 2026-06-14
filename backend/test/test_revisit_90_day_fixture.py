"""PRD §15 criterion #7 — synthetic 90-day revisit dry-run."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from services.notifications import (
    NotificationEvaluationContext,
    NotificationKind,
    ProductNotificationSnapshot,
    ProfileNotificationFlags,
    RecentNotificationRow,
    RevisitOnSaleEvaluator,
    RevisitStaleEvaluator,
    default_composite_evaluator,
)
from services.pricing import ListingDailyObservation


def _build_observations(
    *,
    listing_id,
    start: date,
    days: int,
    baseline_price: int,
    sale_price: int,
    sale_from_offset: int,
) -> list[ListingDailyObservation]:
    observations: list[ListingDailyObservation] = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        price = sale_price if offset >= sale_from_offset else baseline_price
        observations.append(
            ListingDailyObservation(
                listing_id=listing_id,
                observed_on=day,
                price_cents=price,
                is_in_stock=True,
                review_status="accepted",
                is_primary=True,
            )
        )
    return observations


def _evaluate(
    *,
    evaluated_on: date,
    product_created_on: date,
    last_interaction_at: datetime | None,
    observations: list[ListingDailyObservation],
    recent_notifications: list[RecentNotificationRow],
) -> list:
    product_id = uuid4()
    for row in recent_notifications:
        if row.product_id is None:
            row.product_id = product_id

    evaluated_at = datetime.combine(evaluated_on, datetime.min.time(), tzinfo=UTC).replace(
        hour=12
    )
    return default_composite_evaluator().evaluate(
        NotificationEvaluationContext(
            user_id=uuid4(),
            product_id=product_id,
            evaluated_at=evaluated_at,
            scrape_source="scheduled",
            effective_threshold_pct=20,
            profile=ProfileNotificationFlags(
                notifications_enabled=True,
                default_threshold_pct=20,
                revisit_prompts_enabled=True,
                revisit_on_sale_enabled=True,
                revisit_stale_enabled=True,
                revisit_stale_days=30,
            ),
            product=ProductNotificationSnapshot(
                status="active",
                notifications_enabled=True,
                notification_threshold_pct=None,
                created_at=datetime.combine(
                    product_created_on, datetime.min.time(), tzinfo=UTC
                ),
                last_user_interaction_at=last_interaction_at,
            ),
            recent_observations=observations,
            recent_notifications=recent_notifications,
        )
    )


def test_revisit_90_day_fixture_never_repeats_within_debounce():
    listing_id = uuid4()
    start = date(2026, 3, 16)
    observations = _build_observations(
        listing_id=listing_id,
        start=start,
        days=90,
        baseline_price=10000,
        sale_price=8000,
        sale_from_offset=31,
    )

    day32 = start + timedelta(days=31)
    day32_obs = [o for o in observations if o.observed_on <= day32]
    first_on_sale = _evaluate(
        evaluated_on=day32,
        product_created_on=start,
        last_interaction_at=None,
        observations=day32_obs,
        recent_notifications=[],
    )
    first_kinds = [p.type for p in first_on_sale]
    assert NotificationKind.REVISIT_ON_SALE in first_kinds

    day33 = day32 + timedelta(days=1)
    debounced = _evaluate(
        evaluated_on=day33,
        product_created_on=start,
        last_interaction_at=None,
        observations=[o for o in observations if o.observed_on <= day33],
        recent_notifications=[
            RecentNotificationRow(
                type="revisit_on_sale",
                product_id=None,
                created_at=datetime.combine(day32, datetime.min.time(), tzinfo=UTC).replace(
                    hour=12
                ),
            )
        ],
    )
    assert not any(p.type == NotificationKind.REVISIT_ON_SALE for p in debounced)
    assert not any(p.type == NotificationKind.REVISIT_STALE for p in debounced)

    stale_day = start + timedelta(days=60)
    stale_blocked = _evaluate(
        evaluated_on=stale_day,
        product_created_on=start,
        last_interaction_at=None,
        observations=[o for o in observations if o.observed_on <= stale_day],
        recent_notifications=[
            RecentNotificationRow(
                type="revisit_on_sale",
                product_id=None,
                created_at=datetime.combine(day32, datetime.min.time(), tzinfo=UTC).replace(
                    hour=12
                ),
            )
        ],
    )
    assert not any(
        p.type in {NotificationKind.REVISIT_ON_SALE, NotificationKind.REVISIT_STALE}
        for p in stale_blocked
    )

    after_debounce = start + timedelta(days=62)
    refire = _evaluate(
        evaluated_on=after_debounce,
        product_created_on=start,
        last_interaction_at=None,
        observations=[o for o in observations if o.observed_on <= after_debounce],
        recent_notifications=[
            RecentNotificationRow(
                type="revisit_on_sale",
                product_id=None,
                created_at=datetime.combine(day32, datetime.min.time(), tzinfo=UTC).replace(
                    hour=12
                )
                - timedelta(days=31),
            )
        ],
    )
    refire_kinds = [p.type for p in refire]
    assert (
        NotificationKind.REVISIT_ON_SALE in refire_kinds
        or NotificationKind.REVISIT_STALE in refire_kinds
    )

    mutual_day = start + timedelta(days=45)
    mutual_obs = [o for o in observations if o.observed_on <= mutual_day]
    on_sale_alone = RevisitOnSaleEvaluator().evaluate(
        NotificationEvaluationContext(
            user_id=uuid4(),
            product_id=uuid4(),
            evaluated_at=datetime.combine(mutual_day, datetime.min.time(), tzinfo=UTC).replace(
                hour=12
            ),
            scrape_source="scheduled",
            effective_threshold_pct=20,
            profile=ProfileNotificationFlags(
                notifications_enabled=True,
                default_threshold_pct=20,
                revisit_prompts_enabled=True,
                revisit_on_sale_enabled=True,
                revisit_stale_enabled=True,
                revisit_stale_days=30,
            ),
            product=ProductNotificationSnapshot(
                status="active",
                notifications_enabled=True,
                notification_threshold_pct=None,
                created_at=datetime.combine(start, datetime.min.time(), tzinfo=UTC),
                last_user_interaction_at=None,
            ),
            recent_observations=mutual_obs,
            recent_notifications=[],
        )
    )
    stale_alone = RevisitStaleEvaluator().evaluate(
        NotificationEvaluationContext(
            user_id=uuid4(),
            product_id=uuid4(),
            evaluated_at=datetime.combine(mutual_day, datetime.min.time(), tzinfo=UTC).replace(
                hour=12
            ),
            scrape_source="scheduled",
            effective_threshold_pct=20,
            profile=ProfileNotificationFlags(
                notifications_enabled=True,
                default_threshold_pct=20,
                revisit_prompts_enabled=True,
                revisit_on_sale_enabled=True,
                revisit_stale_enabled=True,
                revisit_stale_days=30,
            ),
            product=ProductNotificationSnapshot(
                status="active",
                notifications_enabled=True,
                notification_threshold_pct=None,
                created_at=datetime.combine(start, datetime.min.time(), tzinfo=UTC),
                last_user_interaction_at=None,
            ),
            recent_observations=mutual_obs,
            recent_notifications=[],
        )
    )
    if on_sale_alone:
        assert stale_alone == []

    assert start + timedelta(days=89) == date(2026, 6, 13)
