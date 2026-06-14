"""Per-kind notification evaluator unit tests (T3.4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from services.notifications import (
    BackInStockEvaluator,
    ListingNotificationSnapshot,
    NotificationEvaluationContext,
    NotificationKind,
    PriceDropEvaluator,
    ProductNotificationSnapshot,
    ProfileNotificationFlags,
    RecentNotificationRow,
    RevisitOnSaleEvaluator,
    RevisitStaleEvaluator,
    ScrapeFailingEvaluator,
    default_composite_evaluator,
)
from services.pricing import ListingDailyObservation


def _profile(**overrides) -> ProfileNotificationFlags:
    base = ProfileNotificationFlags(
        notifications_enabled=True,
        default_threshold_pct=20,
        revisit_prompts_enabled=True,
        revisit_on_sale_enabled=True,
        revisit_stale_enabled=True,
        revisit_stale_days=30,
    )
    return base.model_copy(update=overrides)


def _product(**overrides) -> ProductNotificationSnapshot:
    now = datetime(2026, 6, 14, 12, 0, 0, tzinfo=UTC)
    base = ProductNotificationSnapshot(
        status="active",
        notifications_enabled=True,
        notification_threshold_pct=None,
        created_at=now - timedelta(days=60),
        last_user_interaction_at=None,
    )
    return base.model_copy(update=overrides)


def _ctx(**overrides) -> NotificationEvaluationContext:
    user_id = overrides.pop("user_id", uuid4())
    product_id = overrides.pop("product_id", uuid4())
    evaluated_at = overrides.pop(
        "evaluated_at", datetime(2026, 6, 14, 12, 0, 0, tzinfo=UTC)
    )
    recent_notifications = overrides.pop("recent_notifications", [])
    for row in recent_notifications:
        if row.product_id is None:
            row.product_id = product_id

    return NotificationEvaluationContext(
        user_id=user_id,
        product_id=product_id,
        evaluated_at=evaluated_at,
        scrape_source=overrides.pop("scrape_source", "manual"),
        effective_threshold_pct=overrides.pop("effective_threshold_pct", 20),
        profile=overrides.pop("profile", _profile()),
        product=overrides.pop("product", _product()),
        listings=overrides.pop("listings", []),
        recent_observations=overrides.pop("recent_observations", []),
        recent_notifications=recent_notifications,
        **overrides,
    )


def _obs(*, day_offset: int, price: int, listing_id: UUID | None = None) -> ListingDailyObservation:
    evaluated = datetime(2026, 6, 14, 12, 0, 0, tzinfo=UTC)
    day = (evaluated - timedelta(days=day_offset)).date()
    return ListingDailyObservation(
        listing_id=listing_id or uuid4(),
        observed_on=day,
        price_cents=price,
        is_in_stock=True,
        review_status="accepted",
        is_primary=True,
    )


def test_price_drop_fires_at_threshold():
    ctx = _ctx(
        recent_observations=[
            _obs(day_offset=30, price=10000),
            _obs(day_offset=0, price=7500),
        ]
    )
    proposals = PriceDropEvaluator().evaluate(ctx)
    assert len(proposals) == 1
    assert proposals[0].type == NotificationKind.PRICE_DROP
    assert proposals[0].payload == {
        "old_price_cents": 10000,
        "new_price_cents": 7500,
    }


def test_price_drop_skips_below_threshold():
    ctx = _ctx(
        recent_observations=[
            _obs(day_offset=30, price=10000),
            _obs(day_offset=0, price=8500),
        ]
    )
    assert PriceDropEvaluator().evaluate(ctx) == []


@pytest.mark.parametrize(
    "evaluator_cls",
    [
        PriceDropEvaluator,
        BackInStockEvaluator,
        ScrapeFailingEvaluator,
        RevisitOnSaleEvaluator,
        RevisitStaleEvaluator,
    ],
)
def test_notifications_disabled_on_profile_blocks_all(evaluator_cls):
    ctx = _ctx(profile=_profile(notifications_enabled=False))
    assert evaluator_cls().evaluate(ctx) == []


@pytest.mark.parametrize(
    "evaluator_cls",
    [
        PriceDropEvaluator,
        BackInStockEvaluator,
        ScrapeFailingEvaluator,
        RevisitOnSaleEvaluator,
        RevisitStaleEvaluator,
    ],
)
def test_notifications_disabled_on_product_blocks_all(evaluator_cls):
    ctx = _ctx(product=_product(notifications_enabled=False))
    assert evaluator_cls().evaluate(ctx) == []


def test_price_drop_24h_debounce():
    ctx = _ctx(
        recent_observations=[
            _obs(day_offset=30, price=10000),
            _obs(day_offset=0, price=7500),
        ],
        recent_notifications=[
            RecentNotificationRow(
                type="price_drop",
                product_id=None,
                created_at=datetime(2026, 6, 14, 11, 0, 0, tzinfo=UTC),
            )
        ],
    )
    assert PriceDropEvaluator().evaluate(ctx) == []


def test_back_in_stock_false_to_true_only():
    listing_id = uuid4()
    ctx = _ctx(
        listings=[
            ListingNotificationSnapshot(
                id=listing_id,
                retailer_slug="bestbuy_ca",
                is_in_stock=True,
                previous_is_in_stock=False,
                scrape_failure_count=0,
                review_status="accepted",
                is_primary=True,
            )
        ]
    )
    proposals = BackInStockEvaluator().evaluate(ctx)
    assert len(proposals) == 1
    assert proposals[0].payload == {"retailer_slug": "bestbuy_ca"}


def test_back_in_stock_ignores_none_previous():
    ctx = _ctx(
        listings=[
            ListingNotificationSnapshot(
                id=uuid4(),
                retailer_slug="bestbuy_ca",
                is_in_stock=True,
                previous_is_in_stock=None,
                scrape_failure_count=0,
                review_status="accepted",
                is_primary=True,
            )
        ]
    )
    assert BackInStockEvaluator().evaluate(ctx) == []


def test_back_in_stock_24h_debounce():
    listing_id = uuid4()
    ctx = _ctx(
        listings=[
            ListingNotificationSnapshot(
                id=listing_id,
                retailer_slug="bestbuy_ca",
                is_in_stock=True,
                previous_is_in_stock=False,
                scrape_failure_count=0,
                review_status="accepted",
                is_primary=True,
            )
        ],
        recent_notifications=[
            RecentNotificationRow(
                type="back_in_stock",
                listing_id=listing_id,
                created_at=datetime(2026, 6, 14, 11, 0, 0, tzinfo=UTC),
            )
        ],
    )
    assert BackInStockEvaluator().evaluate(ctx) == []


def test_scrape_failing_scheduled_count_three_fires():
    listing_id = uuid4()
    ctx = _ctx(
        scrape_source="scheduled",
        listings=[
            ListingNotificationSnapshot(
                id=listing_id,
                retailer_slug="bestbuy_ca",
                is_in_stock=True,
                previous_is_in_stock=True,
                scrape_failure_count=3,
                review_status="accepted",
                is_primary=True,
            )
        ],
    )
    proposals = ScrapeFailingEvaluator().evaluate(ctx)
    assert len(proposals) == 1
    assert proposals[0].type == NotificationKind.SCRAPE_FAILING


def test_scrape_failing_count_two_does_not_fire():
    ctx = _ctx(
        scrape_source="scheduled",
        listings=[
            ListingNotificationSnapshot(
                id=uuid4(),
                retailer_slug="bestbuy_ca",
                is_in_stock=True,
                previous_is_in_stock=True,
                scrape_failure_count=2,
                review_status="accepted",
                is_primary=True,
            )
        ],
    )
    assert ScrapeFailingEvaluator().evaluate(ctx) == []


def test_scrape_failing_manual_never_fires():
    ctx = _ctx(
        scrape_source="manual",
        listings=[
            ListingNotificationSnapshot(
                id=uuid4(),
                retailer_slug="bestbuy_ca",
                is_in_stock=True,
                previous_is_in_stock=True,
                scrape_failure_count=3,
                review_status="accepted",
                is_primary=True,
            )
        ],
    )
    assert ScrapeFailingEvaluator().evaluate(ctx) == []


def test_scrape_failing_one_shot_no_repeat_at_four():
    listing_id = uuid4()
    ctx = _ctx(
        scrape_source="scheduled",
        listings=[
            ListingNotificationSnapshot(
                id=listing_id,
                retailer_slug="bestbuy_ca",
                is_in_stock=False,
                previous_is_in_stock=True,
                scrape_failure_count=4,
                review_status="accepted",
                is_primary=True,
            )
        ],
    )
    assert ScrapeFailingEvaluator().evaluate(ctx) == []


def test_scrape_failing_refires_after_reset_to_three():
    listing_id = uuid4()
    ctx = _ctx(
        scrape_source="scheduled",
        listings=[
            ListingNotificationSnapshot(
                id=listing_id,
                retailer_slug="bestbuy_ca",
                is_in_stock=False,
                previous_is_in_stock=False,
                scrape_failure_count=3,
                review_status="accepted",
                is_primary=True,
            )
        ],
    )
    assert len(ScrapeFailingEvaluator().evaluate(ctx)) == 1


def test_revisit_on_sale_requires_age_and_discount():
    today = datetime(2026, 6, 14, 12, 0, 0, tzinfo=UTC)
    too_young = _ctx(
        evaluated_at=today,
        product=_product(created_at=today - timedelta(days=20)),
        recent_observations=[
            _obs(day_offset=30, price=10000),
            _obs(day_offset=0, price=8000),
        ],
    )
    assert RevisitOnSaleEvaluator().evaluate(too_young) == []

    eligible = _ctx(
        evaluated_at=today,
        product=_product(created_at=today - timedelta(days=31)),
        recent_observations=[
            _obs(day_offset=30, price=10000),
            _obs(day_offset=0, price=8000),
        ],
    )
    assert len(RevisitOnSaleEvaluator().evaluate(eligible)) == 1


def test_revisit_on_sale_price_drop_overlap_blocks():
    today = datetime(2026, 6, 14, 12, 0, 0, tzinfo=UTC)
    ctx = _ctx(
        evaluated_at=today,
        product=_product(created_at=today - timedelta(days=31)),
        recent_observations=[
            _obs(day_offset=30, price=10000),
            _obs(day_offset=0, price=8000),
        ],
        recent_notifications=[
            RecentNotificationRow(
                type="price_drop",
                product_id=None,
                created_at=today - timedelta(days=3),
            )
        ],
    )
    assert RevisitOnSaleEvaluator().evaluate(ctx) == []


def test_revisit_stale_without_interaction():
    today = datetime(2026, 6, 14, 12, 0, 0, tzinfo=UTC)
    ctx = _ctx(
        evaluated_at=today,
        product=_product(
            created_at=today - timedelta(days=45),
            last_user_interaction_at=None,
        ),
    )
    proposals = RevisitStaleEvaluator().evaluate(ctx)
    assert len(proposals) == 1
    assert proposals[0].type == NotificationKind.REVISIT_STALE


def test_revisit_on_sale_wins_over_stale_same_day():
    today = datetime(2026, 6, 14, 12, 0, 0, tzinfo=UTC)
    ctx = _ctx(
        evaluated_at=today,
        product=_product(
            created_at=today - timedelta(days=45),
            last_user_interaction_at=None,
        ),
        recent_observations=[
            _obs(day_offset=30, price=10000),
            _obs(day_offset=0, price=8000),
        ],
    )
    proposals = default_composite_evaluator().evaluate(ctx)
    kinds = [p.type for p in proposals]
    assert NotificationKind.REVISIT_ON_SALE in kinds
    assert NotificationKind.REVISIT_STALE not in kinds


def test_revisit_30_day_debounce():
    today = datetime(2026, 6, 14, 12, 0, 0, tzinfo=UTC)
    ctx = _ctx(
        evaluated_at=today,
        product=_product(
            created_at=today - timedelta(days=45),
            last_user_interaction_at=None,
        ),
        recent_notifications=[
            RecentNotificationRow(
                type="revisit_stale",
                product_id=None,
                created_at=today - timedelta(days=10),
            )
        ],
    )
    assert RevisitStaleEvaluator().evaluate(ctx) == []

    on_sale_ctx = _ctx(
        evaluated_at=today,
        product=_product(created_at=today - timedelta(days=31)),
        recent_observations=[
            _obs(day_offset=30, price=10000),
            _obs(day_offset=0, price=8000),
        ],
        recent_notifications=[
            RecentNotificationRow(
                type="revisit_on_sale",
                product_id=None,
                created_at=today - timedelta(days=5),
            )
        ],
    )
    assert RevisitOnSaleEvaluator().evaluate(on_sale_ctx) == []
