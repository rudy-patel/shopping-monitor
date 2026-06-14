"""Tests for the Apple Canada scraper."""

from __future__ import annotations

from scrapers.apple_ca import register_apple_ca, scrape
from scrapers.registry import lookup_by_url, reset_registry

IN_STOCK_URL = "https://fixtures.local/apple_ca/in_stock"
OUT_OF_STOCK_URL = "https://fixtures.local/apple_ca/out_of_stock"
MULTI_VARIANT_URL = "https://fixtures.local/apple_ca/multi_variant"
LIVE_DOMAIN_URL = "https://www.apple.com/ca/shop/buy-iphone/iphone-16"
LIVE_CONFIG_URL = (
    "https://www.apple.com/ca/shop/buy-iphone/iphone-16/"
    "6.1-inch-display-128gb-black"
)


def setup_function() -> None:
    reset_registry()
    register_apple_ca()


def test_in_stock_fixture():
    snapshot = scrape(IN_STOCK_URL)
    assert snapshot.retailer_slug == "apple_ca"
    assert "iPhone 16" in snapshot.title
    assert snapshot.current_price_cents > 0
    assert snapshot.currency_seen == "CAD"
    assert snapshot.is_in_stock is True
    assert snapshot.source.value == "fixture"


def test_out_of_stock_fixture():
    snapshot = scrape(OUT_OF_STOCK_URL)
    assert snapshot.is_in_stock is False
    assert snapshot.current_price_cents > 0


def test_multi_variant_fixture():
    snapshot = scrape(MULTI_VARIANT_URL)
    assert snapshot.is_in_stock is True
    assert len(snapshot.available_variants) >= 2
    assert snapshot.selected_variant is not None


def test_lookup_by_live_domain():
    entry = lookup_by_url(LIVE_DOMAIN_URL)
    assert entry.slug == "apple_ca"


def test_lookup_by_live_config_domain():
    entry = lookup_by_url(LIVE_CONFIG_URL)
    assert entry.slug == "apple_ca"
