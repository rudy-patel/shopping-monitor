"""Product API integration tests against live Supabase."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

import scrapers.bootstrap  # noqa: F401
from core.settings import clear_settings_cache
from main import app
from scrapers.bestbuy_ca import extract_bestbuy_html
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret

pytestmark = pytest.mark.integration

_SKIP_REASON = "SUPABASE_URL, SUPABASE_ANON_KEY, or SUPABASE_SERVICE_ROLE_KEY not set"
DEV_USER_ID = "00000000-0000-0000-0000-000000000001"

IN_STOCK_URL = "https://fixtures.local/bestbuy_ca/in_stock"
MULTI_VARIANT_URL = "https://fixtures.local/bestbuy_ca/multi_variant"


def _load_env() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    load_dotenv(backend_root / ".env")


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def _require_supabase_env() -> tuple[str, str, str]:
    _load_env()
    url = _env("SUPABASE_URL")
    anon_key = _env("SUPABASE_ANON_KEY")
    service_key = _env("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not anon_key or not service_key:
        if _env("REQUIRE_INTEGRATION_ENV") == "1":
            pytest.fail(_SKIP_REASON)
        pytest.skip(_SKIP_REASON)
    return url, anon_key, service_key


def _service_client(url: str, service_key: str):
    from supabase import create_client

    return create_client(url, service_key)


def _ensure_dev_auth_user(admin) -> None:
    """Ensure auth-bypass dev user exists for products FK inserts."""
    try:
        users = admin.auth.admin.list_users()
        if any(getattr(user, "id", None) == DEV_USER_ID for user in users):
            return
    except Exception:
        pass
    try:
        admin.auth.admin.create_user(
            {
                "id": DEV_USER_ID,
                "email": "dev-bypass@shopping-monitor.local",
                "email_confirm": True,
            }
        )
    except Exception as exc:
        if "already been registered" not in str(exc).lower():
            raise


def _pink_attrs() -> dict[str, str]:
    html = FixtureLoader().load_text("bestbuy_ca", "multi_variant")
    expected = extract_bestbuy_html(html, url=MULTI_VARIANT_URL)
    pink = next(
        variant
        for variant in expected.available_variants
        if any(attr.attribute_value == "Pink" for attr in variant.attributes)
    )
    return {attr.attribute_name: attr.attribute_value for attr in pink.attributes}


@pytest.fixture
def integration_client(monkeypatch):
    _require_supabase_env()
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "true")
    monkeypatch.setenv("SCRAPER_MODE", "fixtures")
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    clear_settings_cache()
    url, _, service_key = _require_supabase_env()
    admin = _service_client(url, service_key)
    _ensure_dev_auth_user(admin)
    with TestClient(app) as client:
        yield client, admin


def _delete_product(admin, product_id: str) -> None:
    try:
        admin.table("products").delete().eq("id", product_id).execute()
    except Exception:
        pass


def test_product_lifecycle(integration_client):
    client, admin = integration_client
    product_id: str | None = None

    try:
        create = client.post("/api/products", json={"url": IN_STOCK_URL})
        assert create.status_code == 201
        product_id = create.json()["id"]

        listed = client.get("/api/products")
        assert listed.status_code == 200
        assert any(row["id"] == product_id for row in listed.json())

        detail = client.get(f"/api/products/{product_id}")
        assert detail.status_code == 200
        assert detail.json()["discovery_status"] == "complete"

        patched = client.patch(
            f"/api/products/{product_id}",
            json={"notification_threshold_pct": 12},
        )
        assert patched.status_code == 200
        assert patched.json()["notification_threshold_pct"] == 12

        refreshed = client.post(f"/api/products/{product_id}/refresh")
        assert refreshed.status_code == 200
        assert refreshed.json()["last_refresh_at"] is not None

        archived = client.patch(
            f"/api/products/{product_id}",
            json={"status": "archived"},
        )
        assert archived.status_code == 200
        assert archived.json()["status"] == "archived"

        restored = client.patch(
            f"/api/products/{product_id}",
            json={"status": "active"},
        )
        assert restored.status_code == 200
        assert restored.json()["status"] == "active"

        deleted = client.delete(f"/api/products/{product_id}")
        assert deleted.status_code == 204
        product_id = None

        gone = admin.table("products").select("id").eq("id", create.json()["id"]).execute()
        assert not gone.data
    finally:
        if product_id is not None:
            _delete_product(admin, product_id)


def test_needs_input_select_variant_flow(integration_client):
    client, admin = integration_client
    product_id: str | None = None

    try:
        create = client.post("/api/products", json={"url": MULTI_VARIANT_URL})
        assert create.status_code == 201
        product_id = create.json()["id"]
        assert create.json()["status"] == "needs_input"

        selected = client.post(
            f"/api/products/{product_id}/select-variant",
            json={"variant_attributes": _pink_attrs()},
        )
        assert selected.status_code == 200
        assert selected.json()["status"] == "active"
    finally:
        if product_id is not None:
            _delete_product(admin, product_id)
