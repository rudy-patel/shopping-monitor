"""Tests for the Amazon.ca scraper."""

from __future__ import annotations

from scrapers.amazon_ca import register_amazon_ca, scrape
from scrapers.registry import lookup_by_url, reset_registry

IN_STOCK_URL = "https://fixtures.local/amazon_ca/in_stock"
OUT_OF_STOCK_URL = "https://fixtures.local/amazon_ca/out_of_stock"
MULTI_VARIANT_URL = "https://fixtures.local/amazon_ca/multi_variant"
LIVE_DOMAIN_URL = "https://www.amazon.ca/Echo-Dot-5th-Gen-2022-release/dp/B09B8V1LZ3"


def setup_function() -> None:
    reset_registry()
    register_amazon_ca()


def test_in_stock_fixture():
    snapshot = scrape(IN_STOCK_URL)
    assert snapshot.retailer_slug == "amazon_ca"
    assert snapshot.title
    assert "Echo Dot" in snapshot.title
    assert snapshot.current_price_cents == 6999
    assert snapshot.currency_seen == "CAD"
    assert snapshot.is_in_stock is True
    assert snapshot.source.value == "fixture"
    assert len(snapshot.available_variants) >= 2


def test_out_of_stock_fixture():
    snapshot = scrape(OUT_OF_STOCK_URL)
    assert "Echo Dot" in snapshot.title
    assert snapshot.is_in_stock is False
    assert snapshot.current_price_cents == 6999


def test_multi_variant_fixture():
    snapshot = scrape(MULTI_VARIANT_URL)
    assert snapshot.is_in_stock is True
    assert len(snapshot.available_variants) >= 2


def test_lookup_by_live_domain():
    entry = lookup_by_url(LIVE_DOMAIN_URL)
    assert entry.slug == "amazon_ca"
