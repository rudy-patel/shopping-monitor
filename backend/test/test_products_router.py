"""Product router unit tests."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import scrapers.bootstrap  # noqa: F401
from core.settings import clear_settings_cache
from routers.products import router as products_router
from scrapers.bestbuy_ca import extract_bestbuy_html
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret
from services.categorizer import DefaultCategorizer
from services.factory import get_categorizer
from services.llm import FakeLlmProvider, LlmCategorizationResult
from services.profile_service import PROFILE_DEFAULTS
from test.fake_supabase import FakeSupabaseClient

DEV_USER_ID = "00000000-0000-0000-0000-000000000001"
OTHER_USER_ID = "00000000-0000-0000-0000-000000000002"

IN_STOCK_URL = "https://fixtures.local/bestbuy_ca/in_stock"
MULTI_VARIANT_URL = "https://fixtures.local/bestbuy_ca/multi_variant"
GENERIC_BLOCKED_URL = "https://fixtures.local/generic/no_extractable_data"
NON_CAD_URL = "https://fixtures.local/generic/non_cad"


def _pink_variant_url() -> str:
    html = FixtureLoader().load_text("bestbuy_ca", "multi_variant")
    expected = extract_bestbuy_html(html, url=MULTI_VARIANT_URL)
    pink = next(
        variant
        for variant in expected.available_variants
        if any(attr.attribute_value == "Pink" for attr in variant.attributes)
    )
    assert pink.sku is not None
    return f"{MULTI_VARIANT_URL}?sku={pink.sku}"


def make_app(fake_llm: FakeLlmProvider | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(products_router)
    llm = fake_llm or FakeLlmProvider(
        categorize_result=LlmCategorizationResult(category="tech")
    )
    app.dependency_overrides[get_categorizer] = lambda: DefaultCategorizer(
        llm,
        retailer_defaults={"bestbuy_ca": "tech", "generic": "other"},
    )
    return app


@pytest.fixture
def auth_env(monkeypatch):
    snapshot = dict(os.environ)
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    monkeypatch.setenv("SCRAPER_MODE", "fixtures")
    clear_settings_cache()
    yield monkeypatch
    os.environ.clear()
    os.environ.update(snapshot)
    clear_settings_cache()


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeSupabaseClient()
    monkeypatch.setattr("services.product_service.get_client", lambda: client)
    monkeypatch.setattr("services.profile_service.get_client", lambda: client)
    monkeypatch.setattr("services.discovery.get_service_role_client", lambda: client)
    monkeypatch.setattr(
        "services.notification_evaluation.get_or_create_profile",
        lambda user_id: {"user_id": str(user_id), **PROFILE_DEFAULTS},
    )
    return client


@pytest.fixture
def fake_llm():
    return FakeLlmProvider(categorize_result=LlmCategorizationResult(category="tech"))


@pytest.fixture
def products_client(auth_env, fake_client, fake_llm, monkeypatch):
    from scrapers.bestbuy_ca import register_bestbuy_ca
    from scrapers.generic import register_generic

    register_generic()
    register_bestbuy_ca()
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "true")
    clear_settings_cache()
    app = make_app(fake_llm)
    with TestClient(app) as client:
        yield client, fake_client, fake_llm


def _seed_product(
    fake: FakeSupabaseClient,
    *,
    user_id: str = DEV_USER_ID,
    status: str = "active",
    **overrides,
) -> dict:
    now = datetime.now(UTC).isoformat()
    product_id = str(uuid4())
    row = {
        "id": product_id,
        "user_id": user_id,
        "title": "Seeded Product",
        "brand": "Brand",
        "image_url": None,
        "category": "tech",
        "category_source": "heuristic",
        "status": status,
        "notification_threshold_pct": None,
        "notifications_enabled": True,
        "discovery_status": "complete",
        "last_refresh_at": None,
        "last_user_interaction_at": None,
        "created_at": now,
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
        "url": IN_STOCK_URL,
        "variant_attributes": {},
        "available_variants": [],
        "scrape_snapshot": {},
        "is_primary": True,
        "review_status": "accepted",
        "last_known_price_cents": 9999,
        "is_in_stock": True,
        "last_scraped_at": now,
        "scrape_status": "ok",
        "scrape_failure_count": 0,
        "created_at": now,
        "updated_at": now,
        **overrides,
    }
    fake.product_listings[listing_id] = row
    return row


def test_post_bestbuy_in_stock_creates_product(products_client):
    client, fake, _llm = products_client

    response = client.post("/api/products", json={"url": IN_STOCK_URL})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "active"
    assert body["category_source"] in {"heuristic", "llm", "default_other"}
    assert len(body["listings"]) == 1
    assert body["listings"][0]["scrape_status"] == "ok"
    assert body["best_price_cents"] == body["listings"][0]["last_known_price_cents"]
    assert len(fake.products) == 1
    assert len(fake.product_listings) == 1
    assert len(fake.price_history) == 1
    assert list(fake.price_history.values())[0]["source"] == "scheduled"

    detail = client.get(f"/api/products/{body['id']}")
    assert detail.json()["discovery_status"] == "complete"


def test_post_manual_category_skips_llm(products_client, fake_llm):
    client, _fake, llm = products_client

    response = client.post(
        "/api/products",
        json={"url": IN_STOCK_URL, "category": "shoes"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["category"] == "shoes"
    assert body["category_source"] == "manual"
    assert llm.categorize_calls == []


def _post_product_with_llm(
    *,
    fake_llm: FakeLlmProvider,
    auth_env,
    fake_client,
    monkeypatch,
    url: str,
):
    """POST /api/products with a custom fake LLM patched into product_service.

    `product_service.create_product` calls `get_categorizer()` directly (not via
    FastAPI's Depends), so we patch the function at the import site instead of
    using `app.dependency_overrides`.
    """
    from scrapers.bestbuy_ca import register_bestbuy_ca
    from scrapers.generic import register_generic

    register_generic()
    register_bestbuy_ca()
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "true")
    clear_settings_cache()

    categorizer = DefaultCategorizer(
        fake_llm,
        retailer_defaults={"bestbuy_ca": "tech", "generic": "other"},
    )
    monkeypatch.setattr(
        "services.product_service.get_categorizer", lambda: categorizer
    )

    app = make_app(fake_llm)
    with TestClient(app) as client:
        return client.post("/api/products", json={"url": url})


def test_post_uses_llm_clean_title_when_strictly_shorter(
    auth_env, fake_client, monkeypatch
):
    """A meaningfully shorter `clean_title` overrides the verbose scraped title."""
    fake_llm = FakeLlmProvider(
        categorize_result=LlmCategorizationResult(
            category="tech",
            clean_title="Lenovo Yoga Slim 7x",
        )
    )
    response = _post_product_with_llm(
        fake_llm=fake_llm,
        auth_env=auth_env,
        fake_client=fake_client,
        monkeypatch=monkeypatch,
        url=IN_STOCK_URL,
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Lenovo Yoga Slim 7x"


def test_post_keeps_scraped_title_when_clean_title_absent(
    auth_env, fake_client, monkeypatch
):
    """No `clean_title` from LLM → product keeps the scraped title verbatim."""
    fake_llm = FakeLlmProvider(
        categorize_result=LlmCategorizationResult(category="tech")
    )
    response = _post_product_with_llm(
        fake_llm=fake_llm,
        auth_env=auth_env,
        fake_client=fake_client,
        monkeypatch=monkeypatch,
        url=IN_STOCK_URL,
    )

    assert response.status_code == 201
    title = response.json()["title"]
    assert "Lenovo" in title
    assert len(title) > len("Lenovo Yoga Slim 7x")


def test_post_ignores_clean_title_that_matches_scraped(
    auth_env, fake_client, monkeypatch
):
    """An LLM that just echoes the scraped title back is a no-op (no rename)."""
    # Using the in_stock fixture's scraped title verbatim — the override should
    # be skipped (case-insensitive equality short-circuit) so we keep the
    # canonical scraped form for traceability.
    scraped_title = (
        'Lenovo Yoga Slim 7x 14.5" Touchscreen Copilot+ PC Laptop - '
        "Cosmic Blue (Snapdragon X Elite/16GB RAM/1TB SSD)"
    )
    fake_llm = FakeLlmProvider(
        categorize_result=LlmCategorizationResult(
            category="tech",
            clean_title=scraped_title.lower(),
        )
    )
    response = _post_product_with_llm(
        fake_llm=fake_llm,
        auth_env=auth_env,
        fake_client=fake_client,
        monkeypatch=monkeypatch,
        url=IN_STOCK_URL,
    )
    assert response.status_code == 201
    assert response.json()["title"] == scraped_title


def test_post_multi_variant_needs_input(products_client):
    client, fake, _llm = products_client

    response = client.post("/api/products", json={"url": MULTI_VARIANT_URL})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "needs_input"
    primary = next(row for row in body["listings"] if row["is_primary"])
    assert primary["available_variants"]
    needs_input = [
        row for row in fake.notifications.values() if row["type"] == "needs_input"
    ]
    assert len(needs_input) == 1


def test_post_multi_variant_with_sku_is_active(products_client):
    client, _fake, _llm = products_client
    url = _pink_variant_url()

    response = client.post("/api/products", json={"url": url})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "active"
    assert body["listings"][0]["variant_attributes"].get("color") == "Pink"


def test_post_generic_blocked(products_client):
    client, fake, _llm = products_client

    response = client.post("/api/products", json={"url": GENERIC_BLOCKED_URL})

    assert response.status_code == 201
    body = response.json()
    assert body["listings"][0]["scrape_status"] == "blocked"
    assert body["listings"][0]["last_known_price_cents"] is None
    assert len(fake.price_history) == 0


def test_post_with_discovery_seed_payload_accepts(products_client):
    """T8.4: search-flow seed is accepted on POST /api/products."""
    client, _fake, _llm = products_client

    response = client.post(
        "/api/products",
        json={
            "url": IN_STOCK_URL,
            "discovery_seed": [
                {
                    "retailer_slug": "indigo",
                    "url": "https://fixtures.local/indigo/in_stock",
                }
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "active"


def test_post_discovery_seed_invalid_shape_returns_422(products_client):
    client, _fake, _llm = products_client

    response = client.post(
        "/api/products",
        json={
            "url": IN_STOCK_URL,
            "discovery_seed": [{"url": "https://example.ca/p"}],  # missing slug
        },
    )

    assert response.status_code == 422


def test_post_non_cad_rejected(products_client, fake_client):
    client, fake, _llm = products_client

    response = client.post("/api/products", json={"url": NON_CAD_URL})

    assert response.status_code == 422
    assert len(fake.products) == 0


def test_get_list_defaults_to_active(products_client, fake_client):
    client, fake, _llm = products_client
    active = _seed_product(fake, status="active")
    _seed_product(fake, status="archived")
    _seed_listing(fake, active["id"])

    response = client.get("/api/products")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "active"


def test_get_list_archived_filter(products_client, fake_client):
    client, fake, _llm = products_client
    archived = _seed_product(fake, status="archived")
    _seed_product(fake, status="active")
    _seed_listing(fake, archived["id"])

    response = client.get("/api/products", params={"status": "archived"})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "archived"


def test_get_detail_includes_sorted_listings_and_trend(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    _seed_listing(fake, product["id"], last_known_price_cents=5000)
    expensive = _seed_listing(
        fake,
        product["id"],
        last_known_price_cents=9000,
        is_primary=False,
        review_status="accepted",
    )
    fake.price_history[1] = {
        "id": 1,
        "listing_id": expensive["id"],
        "price_cents": 9000,
        "is_in_stock": True,
        "observed_at": datetime.now(UTC).isoformat(),
        "source": "scheduled",
    }

    response = client.get(f"/api/products/{product['id']}")

    assert response.status_code == 200
    body = response.json()
    prices = [listing["last_known_price_cents"] for listing in body["listings"]]
    assert prices == sorted(prices)
    assert "trend" in body
    assert body["trend"]["label"]
    assert body["needs_review_count"] == 0


def test_needs_review_count_increments_for_unreviewed_listings(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    _seed_listing(fake, product["id"], review_status="accepted")
    _seed_listing(
        fake,
        product["id"],
        is_primary=False,
        review_status="needs_review",
        last_known_price_cents=8000,
    )

    response = client.get(f"/api/products/{product['id']}")

    assert response.status_code == 200
    assert response.json()["needs_review_count"] == 1

    list_response = client.get("/api/products")
    assert list_response.json()[0]["needs_review_count"] == 1


def test_patch_updates_category_and_interaction(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    _seed_listing(fake, product["id"])

    response = client.patch(
        f"/api/products/{product['id']}",
        json={"category": "home", "notification_threshold_pct": 15},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "home"
    assert body["category_source"] == "manual"
    assert body["notification_threshold_pct"] == 15
    assert body["last_user_interaction_at"] is not None


def test_patch_restore_archived_product(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake, status="archived")
    _seed_listing(fake, product["id"])

    response = client.patch(
        f"/api/products/{product['id']}",
        json={"status": "active"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_delete_product_cascades(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    listing = _seed_listing(fake, product["id"])
    fake.notifications[str(uuid4())] = {
        "id": str(uuid4()),
        "user_id": DEV_USER_ID,
        "product_id": product["id"],
        "type": "needs_input",
        "payload": {},
        "is_read": False,
        "created_at": datetime.now(UTC).isoformat(),
    }
    fake.price_history[1] = {
        "id": 1,
        "listing_id": listing["id"],
        "price_cents": 1000,
        "is_in_stock": True,
        "observed_at": datetime.now(UTC).isoformat(),
        "source": "scheduled",
    }

    response = client.delete(f"/api/products/{product['id']}")

    assert response.status_code == 204
    assert len(fake.products) == 0
    assert len(fake.product_listings) == 0
    assert len(fake.price_history) == 0
    assert len(fake.notifications) == 0


def test_refresh_success_adds_manual_history(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    _seed_listing(fake, product["id"])

    response = client.post(f"/api/products/{product['id']}/refresh")

    assert response.status_code == 200
    body = response.json()
    assert body["last_refresh_at"] is not None
    manual_rows = [
        row for row in fake.price_history.values() if row["source"] == "manual"
    ]
    assert len(manual_rows) == 1
    assert fake.products[product["id"]]["last_refresh_at"] is not None


def test_refresh_within_cooldown_returns_429(products_client, fake_client):
    client, fake, _llm = products_client
    recent = datetime.now(UTC).isoformat()
    product = _seed_product(fake, last_refresh_at=recent)
    _seed_listing(fake, product["id"])

    response = client.post(f"/api/products/{product['id']}/refresh")

    assert response.status_code == 429


def test_refresh_scrape_failure_marks_failing(products_client, fake_client, monkeypatch):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    listing = _seed_listing(
        fake,
        product["id"],
        url="https://fixtures.local/bestbuy_ca/missing_scenario",
        scrape_snapshot={"title": "Keep me"},
    )

    response = client.post(f"/api/products/{product['id']}/refresh")

    assert response.status_code == 200
    updated = fake.product_listings[listing["id"]]
    assert updated["scrape_status"] == "failing"
    assert updated["scrape_failure_count"] == 1
    assert updated["scrape_snapshot"] == {"title": "Keep me"}
    scrape_failing = [
        row for row in fake.notifications.values() if row["type"] == "scrape_failing"
    ]
    assert scrape_failing == []


def test_refresh_success_resets_scrape_failure_count(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    listing = _seed_listing(
        fake,
        product["id"],
        scrape_failure_count=2,
    )

    response = client.post(f"/api/products/{product['id']}/refresh")

    assert response.status_code == 200
    assert fake.product_listings[listing["id"]]["scrape_failure_count"] == 0


def test_refresh_emits_price_drop_when_threshold_met(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake, notification_threshold_pct=20)
    listing = _seed_listing(fake, product["id"], last_known_price_cents=179999)
    now = datetime.now(UTC)
    history_id = fake._next_price_history_id()
    fake.price_history[history_id] = {
        "id": history_id,
        "listing_id": listing["id"],
        "price_cents": 250000,
        "is_in_stock": True,
        "observed_at": (now - timedelta(days=30)).isoformat(),
        "source": "scheduled",
    }

    response = client.post(f"/api/products/{product['id']}/refresh")

    assert response.status_code == 200
    price_drops = [
        row for row in fake.notifications.values() if row["type"] == "price_drop"
    ]
    assert len(price_drops) == 1
    assert price_drops[0]["payload"]["new_price_cents"] == 179999


def test_refresh_emits_back_in_stock_on_transition(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    listing = _seed_listing(fake, product["id"], is_in_stock=False)

    response = client.post(f"/api/products/{product['id']}/refresh")

    assert response.status_code == 200
    back_in_stock = [
        row for row in fake.notifications.values() if row["type"] == "back_in_stock"
    ]
    assert len(back_in_stock) == 1
    assert back_in_stock[0]["listing_id"] == listing["id"]


def test_refresh_emits_revisit_stale_for_old_untouched_product(products_client, fake_client):
    client, fake, _llm = products_client
    old_created = (datetime.now(UTC) - timedelta(days=45)).isoformat()
    product = _seed_product(
        fake,
        created_at=old_created,
        last_user_interaction_at=None,
    )
    _seed_listing(fake, product["id"])

    response = client.post(f"/api/products/{product['id']}/refresh")

    assert response.status_code == 200
    revisit = [
        row
        for row in fake.notifications.values()
        if row["type"] in {"revisit_on_sale", "revisit_stale"}
    ]
    assert len(revisit) == 1
    assert revisit[0]["type"] == "revisit_stale"


def test_select_variant_on_active_product_returns_409(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake, status="active")
    _seed_listing(fake, product["id"])

    response = client.post(
        f"/api/products/{product['id']}/select-variant",
        json={"variant_attributes": {"color": "Pink"}},
    )

    assert response.status_code == 409


def test_mutating_other_users_product_returns_404(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake, user_id=OTHER_USER_ID)
    _seed_listing(fake, product["id"])

    assert client.patch(f"/api/products/{product['id']}", json={"status": "archived"}).status_code == 404
    assert client.delete(f"/api/products/{product['id']}").status_code == 404
    assert client.post(f"/api/products/{product['id']}/refresh").status_code == 404
    assert (
        client.post(
            f"/api/products/{product['id']}/select-variant",
            json={"variant_attributes": {"color": "Pink"}},
        ).status_code
        == 404
    )
    review = _seed_review_listing(fake, product["id"])
    extra = _seed_listing(
        fake,
        product["id"],
        is_primary=False,
        review_status="auto_added",
    )
    assert (
        client.post(
            f"/api/products/{product['id']}/listings/{review['id']}/accept"
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/products/{product['id']}/listings/{review['id']}/reject"
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/products/{product['id']}/listings/{extra['id']}").status_code
        == 404
    )


def test_select_variant_activates_product(products_client, fake_client):
    client, fake, _llm = products_client
    html = FixtureLoader().load_text("bestbuy_ca", "multi_variant")
    expected = extract_bestbuy_html(html, url=MULTI_VARIANT_URL)
    product = _seed_product(fake, status="needs_input")
    _seed_listing(
        fake,
        product["id"],
        available_variants=[variant.model_dump() for variant in expected.available_variants],
    )

    response = client.post(
        f"/api/products/{product['id']}/select-variant",
        json={"variant_attributes": {"color": "Pink"}},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_select_variant_invalid_attrs_returns_422(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake, status="needs_input")
    _seed_listing(fake, product["id"], available_variants=[])

    response = client.post(
        f"/api/products/{product['id']}/select-variant",
        json={"variant_attributes": {"color": "NotARealColor"}},
    )

    assert response.status_code == 422


def test_wrong_user_gets_404(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake, user_id=OTHER_USER_ID)
    _seed_listing(fake, product["id"])

    response = client.get(f"/api/products/{product['id']}")

    assert response.status_code == 404


def test_patch_empty_body_returns_400(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    _seed_listing(fake, product["id"])

    response = client.patch(f"/api/products/{product['id']}", json={})

    assert response.status_code == 400


def _seed_review_listing(fake: FakeSupabaseClient, product_id: str, **overrides) -> dict:
    defaults = {
        "is_primary": False,
        "review_status": "needs_review",
        "last_known_price_cents": 7500,
        "is_in_stock": True,
        "match_confidence": 0.72,
        "scrape_snapshot": {
            "title": "Candidate at Canadian Tire",
            "discovery_justification": "Same laptop model",
        },
    }
    defaults.update(overrides)
    return _seed_listing(fake, product_id, **defaults)


def test_accept_needs_review_listing(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    _seed_listing(fake, product["id"], last_known_price_cents=9999)
    review = _seed_review_listing(fake, product["id"])

    response = client.post(
        f"/api/products/{product['id']}/listings/{review['id']}/accept"
    )

    assert response.status_code == 200
    body = response.json()
    accepted = next(row for row in body["listings"] if row["id"] == review["id"])
    assert accepted["review_status"] == "accepted"
    assert body["needs_review_count"] == 0
    assert fake.product_listings[review["id"]]["review_status"] == "accepted"


def test_accept_updates_best_price_when_cheaper(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    _seed_listing(fake, product["id"], last_known_price_cents=9999)
    review = _seed_review_listing(
        fake, product["id"], last_known_price_cents=5000, is_in_stock=True
    )

    response = client.post(
        f"/api/products/{product['id']}/listings/{review['id']}/accept"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["best_price_cents"] == 5000


def test_accept_wrong_user_returns_404(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake, user_id=OTHER_USER_ID)
    _seed_listing(fake, product["id"])
    review = _seed_review_listing(fake, product["id"])

    response = client.post(
        f"/api/products/{product['id']}/listings/{review['id']}/accept"
    )

    assert response.status_code == 404


def test_accept_non_review_listing_returns_409(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    accepted = _seed_listing(
        fake,
        product["id"],
        is_primary=False,
        review_status="accepted",
    )

    response = client.post(
        f"/api/products/{product['id']}/listings/{accepted['id']}/accept"
    )

    assert response.status_code == 409


def test_accept_auto_added_returns_409(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    listing = _seed_listing(
        fake,
        product["id"],
        is_primary=False,
        review_status="auto_added",
    )

    response = client.post(
        f"/api/products/{product['id']}/listings/{listing['id']}/accept"
    )

    assert response.status_code == 409


def test_reject_needs_review_listing(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    _seed_listing(fake, product["id"], last_known_price_cents=9999)
    review = _seed_review_listing(
        fake, product["id"], last_known_price_cents=5000, is_in_stock=True
    )

    response = client.post(
        f"/api/products/{product['id']}/listings/{review['id']}/reject"
    )

    assert response.status_code == 200
    body = response.json()
    rejected = next(row for row in body["listings"] if row["id"] == review["id"])
    assert rejected["review_status"] == "rejected"
    assert body["needs_review_count"] == 0
    assert body["best_price_cents"] == 9999


def test_reject_non_review_listing_returns_409(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    listing = _seed_listing(
        fake,
        product["id"],
        is_primary=False,
        review_status="auto_added",
    )

    response = client.post(
        f"/api/products/{product['id']}/listings/{listing['id']}/reject"
    )

    assert response.status_code == 409


def test_delete_non_primary_listing(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    _seed_listing(fake, product["id"])
    extra = _seed_listing(
        fake,
        product["id"],
        is_primary=False,
        review_status="auto_added",
        last_known_price_cents=8000,
    )

    response = client.delete(
        f"/api/products/{product['id']}/listings/{extra['id']}"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["listing_count"] == 1
    assert extra["id"] not in fake.product_listings


def test_delete_primary_returns_409(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    primary = _seed_listing(fake, product["id"])

    response = client.delete(
        f"/api/products/{product['id']}/listings/{primary['id']}"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Cannot remove primary listing"


def test_delete_wrong_user_returns_404(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake, user_id=OTHER_USER_ID)
    _seed_listing(fake, product["id"])
    extra = _seed_listing(
        fake,
        product["id"],
        is_primary=False,
        review_status="accepted",
    )

    response = client.delete(
        f"/api/products/{product['id']}/listings/{extra['id']}"
    )

    assert response.status_code == 404


def test_review_actions_touch_last_user_interaction(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    _seed_listing(fake, product["id"])
    review = _seed_review_listing(fake, product["id"])
    extra = _seed_listing(
        fake,
        product["id"],
        is_primary=False,
        review_status="auto_added",
    )

    assert fake.products[product["id"]]["last_user_interaction_at"] is None

    client.post(f"/api/products/{product['id']}/listings/{review['id']}/accept")
    assert fake.products[product["id"]]["last_user_interaction_at"] is not None
    first_touch = fake.products[product["id"]]["last_user_interaction_at"]

    review2 = _seed_review_listing(fake, product["id"])
    client.post(f"/api/products/{product['id']}/listings/{review2['id']}/reject")
    assert fake.products[product["id"]]["last_user_interaction_at"] != first_touch

    client.delete(f"/api/products/{product['id']}/listings/{extra['id']}")
    assert fake.products[product["id"]]["last_user_interaction_at"] is not None


def test_count_cap_listings_excludes_rejected(products_client, fake_client):
    from services.product_service import count_cap_listings

    client, fake, _llm = products_client
    product = _seed_product(fake)
    _seed_listing(fake, product["id"])
    for _ in range(4):
        _seed_review_listing(fake, product["id"])

    listings = list(fake.product_listings.values())
    assert count_cap_listings(listings) == 5

    review = next(
        row for row in listings if row.get("review_status") == "needs_review"
    )
    client.post(
        f"/api/products/{product['id']}/listings/{review['id']}/reject"
    )

    updated = list(fake.product_listings.values())
    assert count_cap_listings(updated) == 4


def test_serialized_review_fields_on_needs_review(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    _seed_listing(fake, product["id"])
    review = _seed_review_listing(fake, product["id"])

    response = client.get(f"/api/products/{product['id']}")

    assert response.status_code == 200
    listing = next(row for row in response.json()["listings"] if row["id"] == review["id"])
    assert listing["review_reason"] == "Same laptop model"
    assert listing["review_title"] == "Candidate at Canadian Tire"


def test_detail_includes_price_history_30d_ordered_ascending(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    listing = _seed_listing(fake, product["id"], last_known_price_cents=9999)
    now = datetime.now(UTC)
    for offset, price in [(5, 11000), (10, 12500), (20, 10500), (40, 9999)]:
        history_id = fake._next_price_history_id()
        fake.price_history[history_id] = {
            "id": history_id,
            "listing_id": listing["id"],
            "price_cents": price,
            "is_in_stock": True,
            "observed_at": (now - timedelta(days=offset)).isoformat(),
            "source": "scheduled",
        }

    response = client.get(f"/api/products/{product['id']}")

    assert response.status_code == 200
    body = response.json()
    history = body["price_history_30d"]
    assert len(history) == 3
    dates = [row["observed_on"] for row in history]
    assert dates == sorted(dates)
    assert all(isinstance(row["price_cents"], int) for row in history)
    assert {row["price_cents"] for row in history} == {11000, 12500, 10500}


def test_detail_price_history_30d_empty_when_no_observations(products_client, fake_client):
    client, fake, _llm = products_client
    product = _seed_product(fake)
    _seed_listing(fake, product["id"])

    response = client.get(f"/api/products/{product['id']}")

    assert response.status_code == 200
    assert response.json()["price_history_30d"] == []


def test_list_summary_excludes_price_history_30d(products_client, fake_client):
    """Summary endpoints stay lightweight — only the detail payload carries history."""
    client, fake, _llm = products_client
    product = _seed_product(fake)
    listing = _seed_listing(fake, product["id"])
    history_id = fake._next_price_history_id()
    fake.price_history[history_id] = {
        "id": history_id,
        "listing_id": listing["id"],
        "price_cents": 8000,
        "is_in_stock": True,
        "observed_at": datetime.now(UTC).isoformat(),
        "source": "scheduled",
    }

    list_response = client.get("/api/products")

    assert list_response.status_code == 200
    rows = list_response.json()
    assert rows
    assert "price_history_30d" not in rows[0]


def test_detail_price_history_30d_excludes_out_of_window_rows(products_client, fake_client):
    """Observations older than the 30-day trend window must not appear."""
    client, fake, _llm = products_client
    product = _seed_product(fake)
    listing = _seed_listing(fake, product["id"])
    now = datetime.now(UTC)
    for offset in (5, 45):
        history_id = fake._next_price_history_id()
        fake.price_history[history_id] = {
            "id": history_id,
            "listing_id": listing["id"],
            "price_cents": 7000 + offset,
            "is_in_stock": True,
            "observed_at": (now - timedelta(days=offset)).isoformat(),
            "source": "scheduled",
        }

    response = client.get(f"/api/products/{product['id']}")

    assert response.status_code == 200
    history = response.json()["price_history_30d"]
    assert len(history) == 1
    assert history[0]["price_cents"] == 7005


def test_detail_price_history_30d_skips_needs_review_listings(products_client, fake_client):
    """Needs-review and rejected listings must not contribute to the chart series."""
    from datetime import date as date_cls

    client, fake, _llm = products_client
    product = _seed_product(fake)
    primary = _seed_listing(fake, product["id"], last_known_price_cents=10000)
    review = _seed_review_listing(fake, product["id"], last_known_price_cents=1)
    # Anchor history a few days back so it lands inside the window regardless of
    # the test machine's UTC-vs-local boundary at run time.
    observed_at = (
        datetime.combine(date_cls.today(), datetime.min.time())
        .replace(tzinfo=UTC)
        - timedelta(days=2)
    )
    for listing_id, price in ((primary["id"], 10000), (review["id"], 1)):
        history_id = fake._next_price_history_id()
        fake.price_history[history_id] = {
            "id": history_id,
            "listing_id": listing_id,
            "price_cents": price,
            "is_in_stock": True,
            "observed_at": observed_at.isoformat(),
            "source": "scheduled",
        }

    response = client.get(f"/api/products/{product['id']}")

    assert response.status_code == 200
    history = response.json()["price_history_30d"]
    assert history == [
        {"observed_on": observed_at.date().isoformat(), "price_cents": 10000}
    ]


def test_put_dashboard_order_updates_sort_order(products_client, fake_client):
    client, fake, _llm = products_client
    first = _seed_product(fake, title="First")
    second = _seed_product(fake, title="Second")

    response = client.put(
        "/api/products/dashboard-order",
        json={
            "items": [
                {"id": first["id"], "dashboard_sort_order": 1},
                {"id": second["id"], "dashboard_sort_order": 0},
            ]
        },
    )

    assert response.status_code == 204
    assert fake.products[first["id"]]["dashboard_sort_order"] == 1
    assert fake.products[second["id"]]["dashboard_sort_order"] == 0

    listed = client.get("/api/products").json()
    by_id = {row["id"]: row for row in listed}
    assert by_id[first["id"]]["dashboard_sort_order"] == 1
    assert by_id[second["id"]]["dashboard_sort_order"] == 0


def test_put_dashboard_order_rejects_empty_body(products_client):
    client, _fake, _llm = products_client
    response = client.put("/api/products/dashboard-order", json={"items": []})
    assert response.status_code == 422


def test_put_dashboard_order_rejects_other_users_product(products_client, fake_client):
    client, fake, _llm = products_client
    other_product = _seed_product(fake, user_id=OTHER_USER_ID)
    response = client.put(
        "/api/products/dashboard-order",
        json={"items": [{"id": other_product["id"], "dashboard_sort_order": 0}]},
    )
    assert response.status_code == 404
