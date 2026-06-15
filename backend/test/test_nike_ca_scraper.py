"""Tests for the Nike.ca scraper."""

from __future__ import annotations

from scrapers.nike_ca import register_nike_ca, scrape
from scrapers.registry import lookup_by_url, reset_registry

IN_STOCK_URL = "https://fixtures.local/nike_ca/in_stock"
OUT_OF_STOCK_URL = "https://fixtures.local/nike_ca/out_of_stock"
MULTI_VARIANT_URL = "https://fixtures.local/nike_ca/multi_variant"
LIVE_DOMAIN_URL = "https://www.nike.com/ca/t/air-force-1-07-mens-shoes-nM2To5/CW2288-111"


def setup_function() -> None:
    reset_registry()
    register_nike_ca()


def test_in_stock_fixture():
    snapshot = scrape(IN_STOCK_URL)
    assert snapshot.retailer_slug == "nike_ca"
    assert snapshot.title == "Nike Air Force 1 '07 Men's Shoes"
    assert snapshot.current_price_cents == 15000
    assert snapshot.currency_seen == "CAD"
    assert snapshot.is_in_stock is True
    assert snapshot.source.value == "fixture"
    assert len(snapshot.available_variants) >= 2


def test_out_of_stock_fixture():
    snapshot = scrape(OUT_OF_STOCK_URL)
    assert snapshot.title == "Nike Air Force 1 '07 Men's Shoes"
    assert snapshot.is_in_stock is False
    assert snapshot.current_price_cents == 15000


def test_multi_variant_fixture():
    snapshot = scrape(MULTI_VARIANT_URL)
    assert snapshot.is_in_stock is True
    assert len(snapshot.available_variants) >= 2
    assert snapshot.selected_variant is not None


def test_lookup_by_live_domain():
    entry = lookup_by_url(LIVE_DOMAIN_URL)
    assert entry.slug == "nike_ca"
