"""Notification evaluation orchestrator tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from services.notification_evaluation import (
    evaluator_for_mode,
    run_post_scrape_evaluation,
    run_revisit_evaluation_for_active_products,
)
from services.notifications import NotificationKind
from services.profile_service import PROFILE_DEFAULTS
from test.fake_supabase import FakeSupabaseClient

DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeSupabaseClient()
    monkeypatch.setattr("services.notification_evaluation.get_or_create_profile", lambda uid: {
        "user_id": str(uid),
        **PROFILE_DEFAULTS,
    })
    return client


def _seed_product(fake: FakeSupabaseClient, **overrides) -> dict:
    now = datetime.now(UTC).isoformat()
    product_id = str(uuid4())
    row = {
        "id": product_id,
        "user_id": DEV_USER_ID,
        "title": "Eval Product",
        "status": "active",
        "notifications_enabled": True,
        "notification_threshold_pct": 20,
        "created_at": (datetime.now(UTC) - timedelta(days=60)).isoformat(),
        "last_user_interaction_at": None,
        "updated_at": now,
        **overrides,
    }
    fake.products[product_id] = row
    return row


def _seed_listing(fake: FakeSupabaseClient, product_id: str, **overrides) -> dict:
    listing_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    row = {
        "id": listing_id,
        "product_id": product_id,
        "retailer_slug": "bestbuy_ca",
        "url": "https://fixtures.local/bestbuy_ca/in_stock",
        "is_primary": True,
        "review_status": "accepted",
        "is_in_stock": True,
        "scrape_failure_count": 0,
        "last_known_price_cents": 10000,
        "created_at": now,
        "updated_at": now,
        **overrides,
    }
    fake.product_listings[listing_id] = row
    return row


def _seed_history(
    fake: FakeSupabaseClient,
    listing_id: str,
    *,
    price_cents: int,
    observed_at: datetime,
) -> None:
    fake.price_history[fake._next_price_history_id()] = {
        "id": fake._price_history_counter - 1,
        "listing_id": listing_id,
        "price_cents": price_cents,
        "is_in_stock": True,
        "observed_at": observed_at.isoformat(),
        "source": "scheduled",
    }


def test_run_post_scrape_evaluation_persists_price_drop(fake_client):
    product = _seed_product(
        fake_client,
        notification_threshold_pct=20,
        created_at=(datetime.now(UTC) - timedelta(days=10)).isoformat(),
    )
    listing = _seed_listing(fake_client, product["id"])
    today = datetime.now(UTC)
    _seed_history(
        fake_client,
        listing["id"],
        price_cents=10000,
        observed_at=today - timedelta(days=10),
    )
    _seed_history(
        fake_client,
        listing["id"],
        price_cents=7500,
        observed_at=today,
    )
    listings_before = {
        listing["id"]: {
            "is_in_stock": True,
            "scrape_failure_count": 0,
        }
    }

    proposals = run_post_scrape_evaluation(
        fake_client,
        user_id=UUID(DEV_USER_ID),
        product_id=UUID(product["id"]),
        evaluated_at=today,
        scrape_source="manual",
        listings_before=listings_before,
    )

    price_drops = [p for p in proposals if p.type == NotificationKind.PRICE_DROP]
    assert len(price_drops) == 1
    stored = [row for row in fake_client.notifications.values() if row["type"] == "price_drop"]
    assert len(stored) == 1
    assert stored[0]["payload"]["old_price_cents"] == 10000
    assert stored[0]["payload"]["new_price_cents"] == 7500


def test_back_in_stock_transition(fake_client):
    product = _seed_product(
        fake_client,
        created_at=(datetime.now(UTC) - timedelta(days=10)).isoformat(),
    )
    listing = _seed_listing(fake_client, product["id"], is_in_stock=True)
    listings_before = {
        listing["id"]: {
            "is_in_stock": False,
            "scrape_failure_count": 0,
        }
    }

    run_post_scrape_evaluation(
        fake_client,
        user_id=UUID(DEV_USER_ID),
        product_id=UUID(product["id"]),
        evaluated_at=datetime.now(UTC),
        scrape_source="manual",
        listings_before=listings_before,
    )

    stored = [
        row for row in fake_client.notifications.values() if row["type"] == "back_in_stock"
    ]
    assert len(stored) == 1
    assert stored[0]["payload"]["retailer_slug"] == "bestbuy_ca"


def test_debounce_uses_evaluated_at_not_wall_clock(fake_client, monkeypatch):
    product = _seed_product(
        fake_client,
        notification_threshold_pct=20,
        created_at=(datetime.now(UTC) - timedelta(days=10)).isoformat(),
    )
    listing = _seed_listing(fake_client, product["id"])
    evaluated_at = datetime(2026, 6, 14, 12, 0, 0, tzinfo=UTC)
    _seed_history(
        fake_client,
        listing["id"],
        price_cents=10000,
        observed_at=evaluated_at - timedelta(days=10),
    )
    _seed_history(
        fake_client,
        listing["id"],
        price_cents=7500,
        observed_at=evaluated_at,
    )
    fake_client.notifications[str(uuid4())] = {
        "id": str(uuid4()),
        "user_id": DEV_USER_ID,
        "product_id": product["id"],
        "type": "price_drop",
        "payload": {},
        "is_read": False,
        "created_at": (evaluated_at - timedelta(hours=12)).isoformat(),
    }

    proposals = run_post_scrape_evaluation(
        fake_client,
        user_id=UUID(DEV_USER_ID),
        product_id=UUID(product["id"]),
        evaluated_at=evaluated_at,
        scrape_source="manual",
        listings_before={
            listing["id"]: {"is_in_stock": True, "scrape_failure_count": 0}
        },
    )

    assert not any(p.type == NotificationKind.PRICE_DROP for p in proposals)

    later = evaluated_at + timedelta(hours=25)
    proposals_later = run_post_scrape_evaluation(
        fake_client,
        user_id=UUID(DEV_USER_ID),
        product_id=UUID(product["id"]),
        evaluated_at=later,
        scrape_source="manual",
        listings_before={
            listing["id"]: {"is_in_stock": True, "scrape_failure_count": 0}
        },
    )
    assert any(p.type == NotificationKind.PRICE_DROP for p in proposals_later)


def test_scrape_triggered_mode_excludes_revisit_evaluators(fake_client):
    product = _seed_product(
        fake_client,
        created_at=(datetime.now(UTC) - timedelta(days=90)).isoformat(),
        last_user_interaction_at=(datetime.now(UTC) - timedelta(days=60)).isoformat(),
    )
    _seed_listing(fake_client, product["id"], is_in_stock=True)

    evaluator = evaluator_for_mode("scrape_triggered")
    kinds = {child.kind for child in evaluator._evaluators}

    assert NotificationKind.PRICE_DROP in kinds
    assert NotificationKind.REVISIT_ON_SALE not in kinds
    assert NotificationKind.REVISIT_STALE not in kinds


def test_revisit_only_mode_excludes_price_drop(fake_client, monkeypatch):
    product = _seed_product(
        fake_client,
        notification_threshold_pct=20,
        created_at=(datetime.now(UTC) - timedelta(days=10)).isoformat(),
    )
    listing = _seed_listing(fake_client, product["id"])
    today = datetime.now(UTC)
    _seed_history(fake_client, listing["id"], price_cents=10000, observed_at=today - timedelta(days=10))
    _seed_history(fake_client, listing["id"], price_cents=7500, observed_at=today)
    listings_before = {
        listing["id"]: {"is_in_stock": True, "scrape_failure_count": 0}
    }

    proposals = run_post_scrape_evaluation(
        fake_client,
        user_id=UUID(DEV_USER_ID),
        product_id=UUID(product["id"]),
        evaluated_at=today,
        scrape_source="scheduled",
        listings_before=listings_before,
        mode="revisit_only",
    )

    assert not any(p.type == NotificationKind.PRICE_DROP for p in proposals)


def test_run_revisit_evaluation_for_active_products_uses_revisit_only(fake_client, monkeypatch):
    product = _seed_product(
        fake_client,
        notification_threshold_pct=20,
        created_at=(datetime.now(UTC) - timedelta(days=10)).isoformat(),
    )
    listing = _seed_listing(fake_client, product["id"])
    today = datetime.now(UTC)
    _seed_history(fake_client, listing["id"], price_cents=10000, observed_at=today - timedelta(days=10))
    _seed_history(fake_client, listing["id"], price_cents=7500, observed_at=today)

    modes: list[str] = []
    original = run_post_scrape_evaluation

    def tracking_eval(*args, **kwargs):
        modes.append(kwargs.get("mode", "full"))
        return original(*args, **kwargs)

    monkeypatch.setattr(
        "services.notification_evaluation.run_post_scrape_evaluation",
        tracking_eval,
    )

    run_revisit_evaluation_for_active_products(
        fake_client,
        UUID(DEV_USER_ID),
        today,
    )

    assert modes == ["revisit_only"]
