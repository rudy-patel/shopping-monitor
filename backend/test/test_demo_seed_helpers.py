"""Unit tests for production demo seed helpers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest

from scripts.demo_seed_helpers import (
    CATALOG_PATH,
    build_price_history_rows,
    history_days_for_product,
    listing_is_primary,
    load_catalog,
    price_for_day,
    resolve_demo_seed_scope,
    trend_direction_for_series,
    validate_catalog,
)
from services.pricing import MIN_TREND_HISTORY_DAYS, TrendDirection

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_SEED_SCRIPT = _BACKEND_DIR / "scripts" / "seed_demo_data.py"


def test_prod_catalog_loads_and_validates():
    catalog = load_catalog()
    assert len(catalog["products"]) >= 10
    assert len(catalog["notifications"]) >= 5


def test_validate_catalog_rejects_fixtures_local():
    catalog = load_catalog()
    catalog["products"][0]["listings"][0]["url"] = "https://fixtures.local/bestbuy_ca/in_stock"
    with pytest.raises(RuntimeError, match="fixtures.local"):
        validate_catalog(catalog)


@pytest.mark.parametrize(
    ("trend", "expected"),
    [
        ("down", TrendDirection.DOWN),
        ("up", TrendDirection.UP),
        ("same", TrendDirection.SAME),
    ],
)
def test_synthetic_history_produces_expected_trend(trend: str, expected: TrendDirection):
    listing_id = uuid4()
    rows = build_price_history_rows(
        listing_id=str(listing_id),
        current_cents=10000,
        trend=trend,  # type: ignore[arg-type]
        days=32,
        end_date=date(2026, 6, 15),
    )
    assert len(rows) == 32
    direction = trend_direction_for_series(
        rows=rows,
        listing_id=str(listing_id),
        today=date(2026, 6, 15),
    )
    assert direction == expected
    assert rows[-1]["price_cents"] == 10000


def test_price_for_day_monotonic_down():
    prices = [
        price_for_day(day_offset=i, total_days=10, current_cents=8000, trend="down")
        for i in range(10)
    ]
    assert prices[0] > prices[-1] == 8000


def test_listing_is_primary_defaults_for_single_listing():
    assert listing_is_primary({}, listing_count=1) is True
    assert listing_is_primary({"is_primary": False}, listing_count=2) is False
    assert listing_is_primary({"is_primary": True}, listing_count=3) is True


def test_history_days_meets_trend_minimum():
    assert history_days_for_product(status="active", created_days_ago=10, archived_days_ago=0) >= (
        MIN_TREND_HISTORY_DAYS + 1
    )


def test_resolve_demo_seed_scope_prefers_manifest():
    catalog = load_catalog()
    manifest = {
        "email": "demo@example.com",
        "product_ids": ["p1", "p2"],
        "listing_ids": ["l1", "l2"],
    }
    user_products = [
        {"id": "p1", "title": "iPhone 16"},
        {"id": "p3", "title": "User-added product"},
    ]
    product_ids, listing_ids = resolve_demo_seed_scope(
        manifest=manifest,
        email="demo@example.com",
        user_products=user_products,
        catalog=catalog,
    )
    assert product_ids == ["p1", "p2"]
    assert listing_ids == ["l1", "l2"]


def test_resolve_demo_seed_scope_falls_back_to_catalog_titles():
    catalog = load_catalog()
    user_products = [
        {"id": "p1", "title": "iPhone 16"},
        {"id": "p2", "title": "User-added product"},
    ]
    product_ids, listing_ids = resolve_demo_seed_scope(
        manifest=None,
        email="demo@example.com",
        user_products=user_products,
        catalog=catalog,
    )
    assert product_ids == ["p1"]
    assert listing_ids is None


def test_resolve_demo_seed_scope_ignores_manifest_for_other_email():
    catalog = load_catalog()
    manifest = {
        "email": "other@example.com",
        "product_ids": ["p9"],
        "listing_ids": ["l9"],
    }
    user_products = [{"id": "p1", "title": "iPhone 16"}]
    product_ids, listing_ids = resolve_demo_seed_scope(
        manifest=manifest,
        email="demo@example.com",
        user_products=user_products,
        catalog=catalog,
    )
    assert product_ids == ["p1"]
    assert listing_ids is None


def test_seed_script_refuses_refresh_timestamps_in_ci():
    env = os.environ.copy()
    env["CI"] = "true"
    proc = subprocess.run(
        [
            sys.executable,
            str(_SEED_SCRIPT),
            "--email",
            "demo@example.com",
            "--refresh-timestamps",
        ],
        cwd=_BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "Refusing production demo writes in CI" in proc.stderr


def test_seed_script_dry_run_without_credentials(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    proc = subprocess.run(
        [
            sys.executable,
            str(_SEED_SCRIPT),
            "--email",
            "missing@example.com",
            "--dry-run",
        ],
        cwd=_BACKEND_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


def test_seed_script_refuses_apply_in_ci():
    env = os.environ.copy()
    env["CI"] = "true"
    proc = subprocess.run(
        [
            sys.executable,
            str(_SEED_SCRIPT),
            "--email",
            "demo@example.com",
            "--apply",
        ],
        cwd=_BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "Refusing production demo writes in CI" in proc.stderr


def test_catalog_json_is_valid_on_disk():
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    validate_catalog(raw)
