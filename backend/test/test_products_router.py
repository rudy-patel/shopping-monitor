"""Product router unit tests."""

from __future__ import annotations

import os
from datetime import UTC, datetime
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
