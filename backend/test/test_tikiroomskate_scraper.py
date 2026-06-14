"""Tests for the Tiki Room Skateboards scraper."""

from __future__ import annotations

from scrapers.registry import lookup_by_url, reset_registry
from scrapers.tikiroomskate import register_tikiroomskate, scrape

IN_STOCK_URL = "https://fixtures.local/tikiroomskate/in_stock"
OUT_OF_STOCK_URL = "https://fixtures.local/tikiroomskate/out_of_stock"
MULTI_VARIANT_URL = "https://fixtures.local/tikiroomskate/multi_variant"
LIVE_DOMAIN_URL = "https://tikiroomskateboards.com/products/bones-reds-bearings"


def setup_function() -> None:
    reset_registry()
    register_tikiroomskate()


def test_in_stock_fixture():
    snapshot = scrape(IN_STOCK_URL)
    assert snapshot.retailer_slug == "tikiroomskate"
    assert "Bones Reds" in snapshot.title
    assert snapshot.current_price_cents == 3000
    assert snapshot.currency_seen == "CAD"
    assert snapshot.is_in_stock is True
    assert snapshot.source.value == "fixture"


def test_out_of_stock_fixture():
    snapshot = scrape(OUT_OF_STOCK_URL)
    assert snapshot.is_in_stock is False


def test_multi_variant_fixture():
    snapshot = scrape(MULTI_VARIANT_URL)
    assert snapshot.is_in_stock is True
    assert len(snapshot.available_variants) >= 2
    assert any(
        attr.attribute_name == "size"
        for variant in snapshot.available_variants
        for attr in variant.attributes
    )


def test_lookup_by_live_domain():
    entry = lookup_by_url(LIVE_DOMAIN_URL)
    assert entry.slug == "tikiroomskate"
