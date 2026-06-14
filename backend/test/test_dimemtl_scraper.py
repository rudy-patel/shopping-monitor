"""Tests for the DIME MTL scraper."""

from __future__ import annotations

from scrapers.dimemtl import scrape

IN_STOCK_URL = "https://fixtures.local/dimemtl/in_stock"
OUT_OF_STOCK_URL = "https://fixtures.local/dimemtl/out_of_stock"
MULTI_VARIANT_URL = "https://fixtures.local/dimemtl/multi_variant"


def test_in_stock_fixture():
    snapshot = scrape(IN_STOCK_URL)
    assert snapshot.retailer_slug == "dimemtl"
    assert "Lenovo Yoga Slim 7x" in snapshot.title
    assert snapshot.current_price_cents > 0
    assert snapshot.currency_seen == "CAD"
    assert snapshot.is_in_stock is True
    assert snapshot.brand == "LENOVO"
    assert snapshot.source.value == "fixture"


def test_out_of_stock_fixture():
    snapshot = scrape(OUT_OF_STOCK_URL)
    assert snapshot.is_in_stock is False


def test_multi_variant_fixture():
    snapshot = scrape(MULTI_VARIANT_URL)
    assert snapshot.is_in_stock is True
    assert snapshot.current_price_cents > 0
