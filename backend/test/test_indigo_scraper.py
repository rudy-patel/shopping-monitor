"""Tests for the Indigo scraper."""

from __future__ import annotations

from scrapers.indigo import register_indigo, scrape
from scrapers.registry import lookup_by_url, reset_registry

IN_STOCK_URL = "https://fixtures.local/indigo/in_stock"
OUT_OF_STOCK_URL = "https://fixtures.local/indigo/out_of_stock"
MULTI_VARIANT_URL = "https://fixtures.local/indigo/multi_variant"
LIVE_DOMAIN_URL = "https://www.indigo.ca/products/the-will-of-the-many"


def setup_function() -> None:
    reset_registry()
    register_indigo()


def test_in_stock_fixture():
    snapshot = scrape(IN_STOCK_URL)
    assert snapshot.retailer_slug == "indigo"
    assert snapshot.title
    assert "Will of the Many" in snapshot.title
    assert snapshot.current_price_cents > 0
    assert snapshot.currency_seen == "CAD"
    assert snapshot.is_in_stock is True
    assert snapshot.source.value == "fixture"


def test_out_of_stock_fixture():
    snapshot = scrape(OUT_OF_STOCK_URL)
    assert "Dune" in snapshot.title
    assert snapshot.is_in_stock is False
    assert snapshot.current_price_cents > 0


def test_multi_variant_fixture():
    snapshot = scrape(MULTI_VARIANT_URL)
    assert snapshot.is_in_stock is True
    assert len(snapshot.available_variants) >= 2
    assert snapshot.selected_variant is not None


def test_lookup_by_live_domain():
    entry = lookup_by_url(LIVE_DOMAIN_URL)
    assert entry.slug == "indigo"
