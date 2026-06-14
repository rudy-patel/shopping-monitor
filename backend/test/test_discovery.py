"""Discovery orchestrator tests."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from core.settings import clear_settings_cache
from services.discovery import run_discovery_for_product
from services.llm import (
    FakeLlmProvider,
    LlmDiscoveryCandidate,
    LlmDiscoveryResult,
    LlmProviderError,
)
from test.discovery_test_retailers import register_discovery_test_retailers
from test.fake_supabase import FakeSupabaseClient

DEV_USER_ID = "00000000-0000-0000-0000-000000000001"

REF_TITLE = (
    "Lenovo Yoga Slim 7x 14.5\" Touchscreen Copilot+ PC Laptop - "
    "Cosmic Blue (Snapdragon X Elite/16GB RAM/1TB SSD)"
)

DISCOVERY_A_HIGH = "https://fixtures.local/discovery_a/high_match"
DISCOVERY_A_MEDIUM = "https://fixtures.local/discovery_a/medium_match"
DISCOVERY_A_LOW = "https://fixtures.local/discovery_a/low_match"
DISCOVERY_B_HIGH = "https://fixtures.local/discovery_b/high_match"
DISCOVERY_C_HIGH = "https://fixtures.local/discovery_c/high_match"
DIMEMTL_IN_STOCK = "https://fixtures.local/dimemtl/in_stock"
SCRAPE_FAIL_URL = "https://fixtures.local/discovery_a/missing_scenario"


def _candidate(url: str) -> LlmDiscoveryCandidate:
    return LlmDiscoveryCandidate(url=url, justification="test match")


@pytest.fixture
def discovery_env(monkeypatch):
    snapshot = dict(os.environ)
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    monkeypatch.setenv("SCRAPER_MODE", "fixtures")
    clear_settings_cache()

    client = FakeSupabaseClient()
    monkeypatch.setattr("services.product_service.get_client", lambda: client)
    monkeypatch.setattr("services.profile_service.get_client", lambda: client)
    monkeypatch.setattr("services.discovery.get_service_role_client", lambda: client)
    monkeypatch.setattr("db.supabase_client.get_service_role_client", lambda: client)

    from scrapers.bestbuy_ca import register_bestbuy_ca
    from scrapers.dimemtl import register_dimemtl
    from scrapers.generic import register_generic

    register_generic()
    register_bestbuy_ca()
    register_dimemtl()
    register_discovery_test_retailers()

    fake_llm = FakeLlmProvider()
    monkeypatch.setattr(
        "services.discovery.get_llm_provider",
        lambda: fake_llm,
    )

    yield client, fake_llm

    os.environ.clear()
    os.environ.update(snapshot)
    clear_settings_cache()


def _seed_product(
    fake: FakeSupabaseClient,
    *,
    status: str = "active",
    variant_attributes: dict | None = None,
) -> dict:
    now = datetime.now(UTC).isoformat()
    product_id = str(uuid4())
    row = {
        "id": product_id,
        "user_id": DEV_USER_ID,
        "title": REF_TITLE,
        "brand": "LENOVO",
        "image_url": None,
        "category": "tech",
        "category_source": "heuristic",
        "status": status,
        "notification_threshold_pct": None,
        "notifications_enabled": True,
        "discovery_status": "pending",
        "last_refresh_at": None,
        "last_user_interaction_at": None,
        "created_at": now,
        "updated_at": now,
    }
    fake.products[product_id] = row

    listing_id = str(uuid4())
    fake.product_listings[listing_id] = {
        "id": listing_id,
        "product_id": product_id,
        "retailer_slug": "bestbuy_ca",
        "url": "https://fixtures.local/bestbuy_ca/in_stock",
        "variant_attributes": variant_attributes or {},
        "available_variants": [],
        "scrape_snapshot": {},
        "is_primary": True,
        "review_status": "accepted",
        "last_known_price_cents": 179999,
        "is_in_stock": True,
        "last_scraped_at": now,
        "scrape_status": "ok",
        "scrape_failure_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    return row


def _seed_secondary_listing(
    fake: FakeSupabaseClient,
    product_id: str,
    *,
    retailer_slug: str = "discovery_a",
    review_status: str = "accepted",
    url: str = DISCOVERY_A_HIGH,
) -> dict:
    now = datetime.now(UTC).isoformat()
    listing_id = str(uuid4())
    row = {
        "id": listing_id,
        "product_id": product_id,
        "retailer_slug": retailer_slug,
        "url": url,
        "variant_attributes": {},
        "available_variants": [],
        "scrape_snapshot": {},
        "is_primary": False,
        "review_status": review_status,
        "last_known_price_cents": 10000,
        "is_in_stock": True,
        "last_scraped_at": now,
        "scrape_status": "ok",
        "scrape_failure_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    fake.product_listings[listing_id] = row
    return row


def test_auto_add_listing_with_price_history(discovery_env):
    fake, llm = discovery_env
    product = _seed_product(fake)
    llm.discover_result = LlmDiscoveryResult(candidates=[_candidate(DISCOVERY_A_HIGH)])

    run_discovery_for_product(product["id"])

    assert fake.products[product["id"]]["discovery_status"] == "complete"
    discovered = [
        row
        for row in fake.product_listings.values()
        if row["product_id"] == product["id"] and not row["is_primary"]
    ]
    assert len(discovered) == 1
    assert discovered[0]["review_status"] == "auto_added"
    assert discovered[0]["match_confidence"] >= 0.85
    history = [
        row
        for row in fake.price_history.values()
        if row["listing_id"] == discovered[0]["id"]
    ]
    assert len(history) == 1
    assert history[0]["source"] == "scheduled"


def test_needs_review_listing_excluded_from_best_price(discovery_env):
    fake, llm = discovery_env
    product = _seed_product(fake)
    llm.discover_result = LlmDiscoveryResult(candidates=[_candidate(DISCOVERY_A_MEDIUM)])

    run_discovery_for_product(product["id"])

    discovered = [
        row
        for row in fake.product_listings.values()
        if row["product_id"] == product["id"] and not row["is_primary"]
    ]
    assert len(discovered) == 1
    assert discovered[0]["review_status"] == "needs_review"
    assert 0.60 <= discovered[0]["match_confidence"] < 0.85


def test_discard_low_score_adds_no_listing(discovery_env):
    fake, llm = discovery_env
    product = _seed_product(fake)
    llm.discover_result = LlmDiscoveryResult(candidates=[_candidate(DISCOVERY_A_LOW)])

    run_discovery_for_product(product["id"])

    discovered = [
        row
        for row in fake.product_listings.values()
        if row["product_id"] == product["id"] and not row["is_primary"]
    ]
    assert discovered == []


def test_total_listing_cap_stops_at_five(discovery_env):
    fake, llm = discovery_env
    product = _seed_product(fake)
    for slug, url in [
        ("discovery_a", DISCOVERY_A_HIGH),
        ("discovery_b", DISCOVERY_B_HIGH),
        ("dimemtl", DIMEMTL_IN_STOCK),
        ("discovery_c", DISCOVERY_C_HIGH),
    ]:
        _seed_secondary_listing(fake, product["id"], retailer_slug=slug, url=url)

    llm.discover_result = LlmDiscoveryResult(
        candidates=[_candidate("https://fixtures.local/discovery_a/medium_match")]
    )

    run_discovery_for_product(product["id"])

    listings = [
        row for row in fake.product_listings.values() if row["product_id"] == product["id"]
    ]
    assert len(listings) == 5


def test_auto_add_cap_stops_without_needs_review(discovery_env):
    fake, llm = discovery_env
    product = _seed_product(fake)
    llm.discover_result = LlmDiscoveryResult(
        candidates=[
            _candidate(DISCOVERY_A_HIGH),
            _candidate(DISCOVERY_B_HIGH),
            _candidate(DIMEMTL_IN_STOCK),
            _candidate(DISCOVERY_C_HIGH),
            _candidate(DISCOVERY_A_MEDIUM),
        ]
    )

    run_discovery_for_product(product["id"])

    listings = [
        row for row in fake.product_listings.values() if row["product_id"] == product["id"]
    ]
    auto_added = [
        row for row in listings if not row["is_primary"] and row["review_status"] == "auto_added"
    ]
    needs_review = [
        row for row in listings if row["review_status"] == "needs_review"
    ]
    assert len(auto_added) == 4
    assert needs_review == []


def test_llm_failure_completes_without_notification(discovery_env):
    fake, llm = discovery_env
    product = _seed_product(fake)
    llm.raise_on_discover = LlmProviderError("boom")

    run_discovery_for_product(product["id"])

    assert fake.products[product["id"]]["discovery_status"] == "complete"
    assert not any(row["type"] == "discovery_complete" for row in fake.notifications.values())


def test_all_discarded_completes_without_notification(discovery_env):
    fake, llm = discovery_env
    product = _seed_product(fake)
    llm.discover_result = LlmDiscoveryResult(
        candidates=[_candidate(DISCOVERY_A_LOW), _candidate(DISCOVERY_A_LOW)]
    )

    run_discovery_for_product(product["id"])

    assert fake.products[product["id"]]["discovery_status"] == "complete"
    assert not any(row["type"] == "discovery_complete" for row in fake.notifications.values())


def test_mixed_auto_added_writes_one_notification(discovery_env):
    fake, llm = discovery_env
    product = _seed_product(fake)
    llm.discover_result = LlmDiscoveryResult(candidates=[_candidate(DISCOVERY_A_HIGH)])

    run_discovery_for_product(product["id"])

    notifications = [
        row for row in fake.notifications.values() if row["type"] == "discovery_complete"
    ]
    assert len(notifications) == 1
    assert notifications[0]["payload"] == {
        "auto_added_count": 1,
        "needs_review_count": 0,
    }


def test_scrape_failure_skips_candidate_and_continues(discovery_env):
    fake, llm = discovery_env
    product = _seed_product(fake)
    llm.discover_result = LlmDiscoveryResult(
        candidates=[_candidate(SCRAPE_FAIL_URL), _candidate(DISCOVERY_A_HIGH)]
    )

    run_discovery_for_product(product["id"])

    discovered = [
        row
        for row in fake.product_listings.values()
        if row["product_id"] == product["id"] and not row["is_primary"]
    ]
    assert len(discovered) == 1
    assert discovered[0]["review_status"] == "auto_added"


def test_duplicate_retailer_keeps_first_url(discovery_env):
    fake, llm = discovery_env
    product = _seed_product(fake)
    llm.discover_result = LlmDiscoveryResult(
        candidates=[
            _candidate(DISCOVERY_A_HIGH),
            _candidate(DISCOVERY_A_MEDIUM),
        ]
    )

    run_discovery_for_product(product["id"])

    discovered = [
        row
        for row in fake.product_listings.values()
        if row["product_id"] == product["id"] and row["retailer_slug"] == "discovery_a"
    ]
    assert len(discovered) == 1
    assert discovered[0]["url"] == DISCOVERY_A_HIGH


def test_needs_input_product_runs_with_empty_variants(discovery_env):
    fake, llm = discovery_env
    product = _seed_product(fake, status="needs_input", variant_attributes={})
    llm.discover_result = LlmDiscoveryResult(candidates=[_candidate(DISCOVERY_A_HIGH)])

    run_discovery_for_product(product["id"])

    assert llm.discover_calls[-1]["variant_attributes"] == {}
    assert llm.discover_calls[-1]["reference_price_cents"] == 179999
    discovered = [
        row
        for row in fake.product_listings.values()
        if row["product_id"] == product["id"] and not row["is_primary"]
    ]
    assert len(discovered) == 1


def test_dimemtl_fixture_cross_retailer_discovery(discovery_env):
    fake, llm = discovery_env
    product = _seed_product(fake)
    llm.discover_result = LlmDiscoveryResult(candidates=[_candidate(DIMEMTL_IN_STOCK)])

    run_discovery_for_product(product["id"])

    discovered = [
        row
        for row in fake.product_listings.values()
        if row["product_id"] == product["id"] and row["retailer_slug"] == "dimemtl"
    ]
    assert len(discovered) == 1
    assert discovered[0]["review_status"] == "auto_added"


def test_discovery_status_transitions_pending_to_running_to_complete(discovery_env):
    fake, llm = discovery_env
    product = _seed_product(fake)
    llm.discover_result = LlmDiscoveryResult(candidates=[])

    run_discovery_for_product(product["id"])

    assert fake.products[product["id"]]["discovery_status"] == "complete"
