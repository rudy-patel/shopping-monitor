"""Tests for the Best Buy Canada scraper."""

from __future__ import annotations

import pytest

from scrapers.bestbuy_ca import extract_bestbuy_html, scrape
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret

IN_STOCK_URL = "https://fixtures.local/bestbuy_ca/in_stock"
OUT_OF_STOCK_URL = "https://fixtures.local/bestbuy_ca/out_of_stock"
MULTI_VARIANT_URL = "https://fixtures.local/bestbuy_ca/multi_variant"


def _expected_from_fixture(scenario: str):
    html = FixtureLoader().load_text("bestbuy_ca", scenario)
    return extract_bestbuy_html(html, url=f"https://fixtures.local/bestbuy_ca/{scenario}")


@pytest.fixture(scope="module")
def in_stock_expected():
    return _expected_from_fixture("in_stock")


@pytest.fixture(scope="module")
def multi_variant_expected():
    return _expected_from_fixture("multi_variant")


def test_in_stock_extracts_core_fields(in_stock_expected):
    snapshot = scrape(IN_STOCK_URL)
    assert snapshot.title == in_stock_expected.title
    assert snapshot.current_price_cents == in_stock_expected.price_cents
    assert snapshot.current_price_cents > 0
    assert snapshot.currency_seen == "CAD"
    assert snapshot.is_in_stock is True
    assert snapshot.brand == in_stock_expected.brand
    assert snapshot.image_url is not None
    assert snapshot.breadcrumbs
    assert snapshot.raw_snapshot["extraction"] == "jsonld"
    assert snapshot.raw_snapshot["sku"]
    assert "Product" in snapshot.raw_snapshot["schema_types"]
    assert snapshot.raw_snapshot["product_id"] == in_stock_expected.raw_snapshot["product_id"]
    assert snapshot.source.value == "fixture"


def test_out_of_stock():
    snapshot = scrape(OUT_OF_STOCK_URL)
    assert snapshot.is_in_stock is False
    assert snapshot.current_price_cents > 0
    assert snapshot.title


def test_multi_variant_lists_combinations(multi_variant_expected):
    snapshot = scrape(MULTI_VARIANT_URL)
    assert len(snapshot.available_variants) >= 2
    assert {variant.sku for variant in snapshot.available_variants if variant.sku} == {
        variant.sku for variant in multi_variant_expected.available_variants if variant.sku
    }
    colors = {
        attr.attribute_value
        for variant in snapshot.available_variants
        for attr in variant.attributes
        if attr.attribute_name == "color"
    }
    assert len(colors) >= 2


def test_multi_variant_ambiguous():
    snapshot = scrape(MULTI_VARIANT_URL)
    assert snapshot.selected_variant is None


def test_multi_variant_sku_query(multi_variant_expected):
    pink = next(
        variant
        for variant in multi_variant_expected.available_variants
        if any(attr.attribute_value == "Pink" for attr in variant.attributes)
    )
    assert pink.sku is not None
    url = f"{MULTI_VARIANT_URL}?sku={pink.sku}"
    snapshot = scrape(url)
    assert snapshot.selected_variant is not None
    assert any(attr.attribute_value == "Pink" for attr in snapshot.selected_variant)


def test_fixture_mode_no_network(monkeypatch):
    def fail_fetch(*_args, **_kwargs):
        pytest.fail("network must not be opened")

    monkeypatch.setattr("scrapers.bestbuy_ca.scraper_fetch", fail_fetch)
    snapshot = scrape(IN_STOCK_URL)
    assert snapshot.title
