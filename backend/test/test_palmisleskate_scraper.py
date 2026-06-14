"""Tests for the Palm Isle Skate Shop scraper."""

from __future__ import annotations

from scrapers.palmisleskate import register_palmisleskate, scrape
from scrapers.registry import lookup_by_url, reset_registry

IN_STOCK_URL = "https://fixtures.local/palmisleskate/in_stock"
OUT_OF_STOCK_URL = "https://fixtures.local/palmisleskate/out_of_stock"
MULTI_VARIANT_URL = "https://fixtures.local/palmisleskate/multi_variant"
LIVE_DOMAIN_URL = "https://palmisleskateshop.com/products/bones-reds-bearings"


def setup_function() -> None:
    reset_registry()
    register_palmisleskate()


def test_in_stock_fixture():
    snapshot = scrape(IN_STOCK_URL)
    assert snapshot.retailer_slug == "palmisleskate"
    assert "Reds Bearings" in snapshot.title
    assert snapshot.current_price_cents == 2800
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
    assert snapshot.selected_variant is not None


def test_lookup_by_live_domain():
    entry = lookup_by_url(LIVE_DOMAIN_URL)
    assert entry.slug == "palmisleskate"
