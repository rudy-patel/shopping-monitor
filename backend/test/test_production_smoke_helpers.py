"""Unit tests for T6.2 production smoke helpers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.production_smoke_helpers import (
    RETAILERS,
    listing_price_cents,
    summarize_add_result,
    validate_add_response,
)

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_SCRIPT = _BACKEND_DIR / "scripts" / "smoke_production_t6_2.py"


def _sample_body(*, retailer_slug: str = "bestbuy_ca") -> dict:
    return {
        "id": "11111111-1111-1111-1111-111111111111",
        "title": "Sample Product",
        "category": "tech",
        "category_source": "llm",
        "listings": [
            {
                "is_primary": True,
                "retailer_slug": retailer_slug,
                "scrape_status": "ok",
                "last_known_price_cents": 12345,
            }
        ],
    }


def test_retailers_include_bestbuy_and_shopify():
    slugs = {row["slug"] for row in RETAILERS}
    assert slugs == {"bestbuy_ca", "palmisleskate"}


def test_listing_price_cents_prefers_last_known():
    assert listing_price_cents({"last_known_price_cents": 2800}) == 2800
    assert listing_price_cents({"price_cents": 999}) == 999


def test_validate_add_response_accepts_valid_body():
    validate_add_response(
        _sample_body(),
        expected_retailer="bestbuy_ca",
        max_seconds=10.0,
        elapsed=2.5,
    )


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (lambda body: body.update({"title": ""}), "missing title/price"),
        (lambda body: body["listings"][0].update({"scrape_status": "blocked"}), "scrape_status"),
        (lambda body: body["listings"][0].update({"retailer_slug": "generic"}), "expected retailer"),
        (lambda body: body.update({"category": "invalid"}), "unexpected category"),
    ],
)
def test_validate_add_response_rejects_invalid_body(mutator, match: str):
    body = _sample_body()
    mutator(body)
    with pytest.raises(RuntimeError, match=match):
        validate_add_response(
            body,
            expected_retailer="bestbuy_ca",
            max_seconds=10.0,
            elapsed=1.0,
        )


def test_validate_add_response_rejects_slow_add():
    with pytest.raises(RuntimeError, match="add exceeded"):
        validate_add_response(
            _sample_body(),
            expected_retailer="bestbuy_ca",
            max_seconds=1.0,
            elapsed=1.5,
        )


def test_summarize_add_result_shape():
    summary = summarize_add_result(
        _sample_body(retailer_slug="palmisleskate"),
        retailer="palmisleskate",
        url="https://example.test/product",
        elapsed=3.25,
        refresh_status=200,
    )
    assert summary["retailer"] == "palmisleskate"
    assert summary["price_cents"] == 12345
    assert summary["refresh_ok"] is True


def test_smoke_script_dry_run_lists_retailers():
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=_BACKEND_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["mode"] == "dry_run"
    assert len(payload["retailers"]) == 2


def test_smoke_script_refuses_live_in_ci():
    env = os.environ.copy()
    env["CI"] = "true"
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--live"],
        cwd=_BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "Refusing --live" in proc.stderr
