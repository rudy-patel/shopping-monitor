"""Scrape-all job service unit tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from services.product_service import ScrapeOutcome
from services.scrape_job_service import (
    load_listings_for_scheduled_scrape,
    run_scrape_all,
    scrape_listing_with_retry,
)
from scrapers.contract import ProductSnapshot, ScrapeSource, utc_now
from scrapers.registry import RetailerEntry
from test.fake_supabase import FakeSupabaseClient

DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeSupabaseClient()
    monkeypatch.setattr(
        "services.notification_evaluation.get_or_create_profile",
        lambda uid: {
            "user_id": str(uid),
            "notifications_enabled": True,
            "default_threshold_pct": 20,
            "revisit_prompts_enabled": True,
            "revisit_on_sale_enabled": True,
            "revisit_stale_enabled": True,
            "revisit_stale_days": 30,
        },
    )
    return client


def _make_entry() -> RetailerEntry:
    return RetailerEntry(
        slug="bestbuy_ca",
        domains=("bestbuy.ca",),
        default_category="tech",
        scrape=lambda url: ProductSnapshot(
            retailer_slug="bestbuy_ca",
            url=url,
            title="Fixture",
            current_price_cents=10000,
            currency_seen="CAD",
            is_in_stock=True,
            scraped_at=utc_now(),
            source=ScrapeSource.FIXTURE,
        ),
        default_strategy=ScrapeSource.FIXTURE,
    )


def _make_outcome(*, status: str = "ok", price: int | None = 10000) -> ScrapeOutcome:
    entry = _make_entry()
    return ScrapeOutcome(
        entry=entry,
        snapshot=ProductSnapshot(
            retailer_slug="bestbuy_ca",
            url="https://fixtures.local/bestbuy_ca/in_stock",
            title="Fixture",
            current_price_cents=price or 0,
            currency_seen="CAD",
            is_in_stock=True,
            scraped_at=utc_now(),
            source=ScrapeSource.FIXTURE,
        ),
        scrape_status=status,  # type: ignore[arg-type]
        price_cents=price,
    )


def _seed_product(
    fake: FakeSupabaseClient,
    *,
    status: str = "active",
    user_id: str = DEV_USER_ID,
) -> dict:
    product_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    row = {
        "id": product_id,
        "user_id": user_id,
        "title": "Scrape Product",
        "status": status,
        "notifications_enabled": True,
        "notification_threshold_pct": 20,
        "created_at": (datetime.now(UTC) - timedelta(days=60)).isoformat(),
        "last_user_interaction_at": None,
        "updated_at": now,
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


def test_run_scrape_all_skipped_when_lock_not_acquired(fake_client):
    fake_client.rpc_returns["try_acquire_scrape_all_lock"] = False

    result = run_scrape_all(fake_client)

    assert result.status == "skipped"
    assert result.reason == "lock_not_acquired"
    assert result.listings_total == 0


def test_load_listings_includes_needs_input_and_rejected(fake_client):
    active = _seed_product(fake_client, status="active")
    needs_input = _seed_product(fake_client, status="needs_input")
    archived = _seed_product(fake_client, status="archived")
    accepted = _seed_listing(fake_client, active["id"], review_status="accepted")
    rejected = _seed_listing(fake_client, needs_input["id"], review_status="rejected")
    _seed_listing(fake_client, archived["id"])

    listings = load_listings_for_scheduled_scrape(fake_client)
    listing_ids = {row["id"] for row in listings}

    assert accepted["id"] in listing_ids
    assert rejected["id"] in listing_ids
    assert all(row.get("user_id") for row in listings)
    assert len(listings) == 2


def test_scrape_listing_with_retry_sleeps_between_attempts(monkeypatch):
    sleep_calls: list[float] = []
    monkeypatch.setattr("services.scrape_job_service.time.sleep", lambda s: sleep_calls.append(s))

    outcomes = [
        _make_outcome(status="failing", price=None),
        _make_outcome(status="failing", price=None),
        _make_outcome(status="ok"),
    ]
    monkeypatch.setattr(
        "services.scrape_job_service.scrape_listing_url",
        lambda **_: outcomes.pop(0),
    )

    result = scrape_listing_with_retry(
        retailer_slug="bestbuy_ca",
        url="https://fixtures.local/bestbuy_ca/in_stock",
    )

    assert result.scrape_status == "ok"
    assert sleep_calls == [1, 2]


def test_scrape_listing_with_retry_does_not_retry_blocked(monkeypatch):
    sleep = MagicMock()
    monkeypatch.setattr("services.scrape_job_service.time.sleep", sleep)
    monkeypatch.setattr(
        "services.scrape_job_service.scrape_listing_url",
        lambda **_: _make_outcome(status="blocked", price=None),
    )

    result = scrape_listing_with_retry(
        retailer_slug="bestbuy_ca",
        url="https://fixtures.local/bestbuy_ca/in_stock",
    )

    assert result.scrape_status == "blocked"
    sleep.assert_not_called()


def test_run_scrape_all_persists_scheduled_price_history(fake_client, monkeypatch):
    product = _seed_product(fake_client)
    listing = _seed_listing(fake_client, product["id"])
    monkeypatch.setattr(
        "services.scrape_job_service.scrape_listing_with_retry",
        lambda **_: _make_outcome(status="ok"),
    )
    monkeypatch.setattr(
        "services.scrape_job_service.run_post_scrape_evaluation",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        "services.scrape_job_service.run_revisit_evaluation_for_active_products",
        lambda *args, **kwargs: [],
    )

    result = run_scrape_all(fake_client)

    assert result.status == "completed"
    history = list(fake_client.price_history.values())
    assert len(history) == 1
    assert history[0]["listing_id"] == listing["id"]
    assert history[0]["source"] == "scheduled"


def test_run_scrape_all_step6_uses_scrape_triggered_mode(fake_client, monkeypatch):
    product = _seed_product(fake_client, status="active")
    _seed_listing(fake_client, product["id"])
    modes: list[str] = []

    def capture_eval(client, *, user_id, product_id, mode="full", **kwargs):
        modes.append(mode)
        return []

    monkeypatch.setattr(
        "services.scrape_job_service.scrape_listing_with_retry",
        lambda **_: _make_outcome(status="ok"),
    )
    monkeypatch.setattr(
        "services.scrape_job_service.run_post_scrape_evaluation",
        capture_eval,
    )
    monkeypatch.setattr(
        "services.scrape_job_service.run_revisit_evaluation_for_active_products",
        lambda *args, **kwargs: [],
    )

    run_scrape_all(fake_client)

    assert modes == ["scrape_triggered"]


def test_run_scrape_all_step6_only_touched_products(fake_client, monkeypatch):
    product_a = _seed_product(fake_client, status="active")
    product_b = _seed_product(fake_client, status="archived")
    _seed_listing(fake_client, product_a["id"])
    _seed_listing(fake_client, product_b["id"])

    evaluated: list[UUID] = []

    def capture_eval(client, *, user_id, product_id, **kwargs):
        evaluated.append(product_id)
        return []

    monkeypatch.setattr(
        "services.scrape_job_service.scrape_listing_with_retry",
        lambda **_: _make_outcome(status="ok"),
    )
    monkeypatch.setattr(
        "services.scrape_job_service.run_post_scrape_evaluation",
        capture_eval,
    )
    monkeypatch.setattr(
        "services.scrape_job_service.run_revisit_evaluation_for_active_products",
        lambda *args, **kwargs: [],
    )

    run_scrape_all(fake_client)

    assert evaluated == [UUID(product_a["id"])]


def test_run_scrape_all_step7_revisit_per_active_user(fake_client, monkeypatch):
    user_a = DEV_USER_ID
    user_b = str(uuid4())
    product_a = _seed_product(fake_client, user_id=user_a)
    product_b = _seed_product(fake_client, user_id=user_b)
    _seed_listing(fake_client, product_a["id"])
    _seed_listing(fake_client, product_b["id"])

    revisit_users: list[UUID] = []

    def capture_revisit(client, user_id, evaluated_at, **kwargs):
        revisit_users.append(user_id)
        return []

    monkeypatch.setattr(
        "services.scrape_job_service.scrape_listing_with_retry",
        lambda **_: _make_outcome(status="ok"),
    )
    monkeypatch.setattr(
        "services.scrape_job_service.run_post_scrape_evaluation",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        "services.scrape_job_service.run_revisit_evaluation_for_active_products",
        capture_revisit,
    )

    result = run_scrape_all(fake_client)

    assert result.users_revisit_evaluated == 2
    assert set(revisit_users) == {UUID(user_a), UUID(user_b)}


def test_run_scrape_all_logs_low_success_rate(fake_client, monkeypatch, caplog):
    import logging

    product = _seed_product(fake_client)
    _seed_listing(fake_client, product["id"])
    _seed_listing(fake_client, product["id"])

    call_count = {"n": 0}

    def flaky_scrape(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _make_outcome(status="ok")
        return _make_outcome(status="failing", price=None)

    monkeypatch.setattr(
        "services.scrape_job_service.scrape_listing_with_retry",
        flaky_scrape,
    )
    monkeypatch.setattr(
        "services.scrape_job_service.run_post_scrape_evaluation",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        "services.scrape_job_service.run_revisit_evaluation_for_active_products",
        lambda *args, **kwargs: [],
    )

    with caplog.at_level(logging.WARNING):
        result = run_scrape_all(fake_client)

    assert result.status == "completed"
    assert result.success_rate < 0.80
    assert any("scrape_all_low_success_rate" in record.message for record in caplog.records)


def test_run_scrape_all_releases_lock_on_error(fake_client, monkeypatch):
    release_calls: list[str] = []
    original_rpc = fake_client.rpc

    def tracking_rpc(name: str):
        rpc = original_rpc(name)
        original_execute = rpc.execute

        def execute():
            if name == "release_scrape_all_lock":
                release_calls.append(name)
            return original_execute()

        rpc.execute = execute  # type: ignore[method-assign]
        return rpc

    fake_client.rpc = tracking_rpc  # type: ignore[method-assign]

    monkeypatch.setattr(
        "services.scrape_job_service.load_listings_for_scheduled_scrape",
        lambda client: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError, match="boom"):
        run_scrape_all(fake_client)

    assert release_calls == ["release_scrape_all_lock"]
