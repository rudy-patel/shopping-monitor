"""Retailer registry tests."""

from __future__ import annotations

import pytest

from scrapers.contract import ProductSnapshot, ScrapeSource, utc_now
from scrapers.exceptions import RetailerAlreadyRegisteredError, RetailerNotSupportedError
from scrapers.registry import RetailerEntry, all_retailers, get, lookup_by_url, register

EXAMPLE_RETAILER_SLUG = "_example_retailer"


def _example_scrape(url: str) -> ProductSnapshot:
    return ProductSnapshot(
        retailer_slug=EXAMPLE_RETAILER_SLUG,
        url=url,
        title="Example Widget",
        current_price_cents=2999,
        currency_seen="CAD",
        is_in_stock=True,
        scraped_at=utc_now(),
        source=ScrapeSource.FIXTURE,
    )


def test_get_example_retailer():
    entry = get(EXAMPLE_RETAILER_SLUG)
    assert entry.slug == EXAMPLE_RETAILER_SLUG


def test_all_retailers_contains_example():
    slugs = {entry.slug for entry in all_retailers()}
    assert EXAMPLE_RETAILER_SLUG in slugs


def test_lookup_by_url_exact_host():
    entry = lookup_by_url("https://example-retailer.test/foo")
    assert entry.slug == EXAMPLE_RETAILER_SLUG


def test_lookup_by_url_trailing_www():
    entry = lookup_by_url("https://www.example-retailer.test/foo")
    assert entry.slug == EXAMPLE_RETAILER_SLUG


def test_lookup_by_url_subdomain_suffix():
    entry = lookup_by_url("https://shop.example-retailer.test/foo")
    assert entry.slug == EXAMPLE_RETAILER_SLUG


@pytest.mark.no_generic_registry
def test_lookup_unknown_raises_when_no_generic():
    with pytest.raises(RetailerNotSupportedError):
        lookup_by_url("https://unknown.example/x")


def test_lookup_falls_back_to_generic():
    entry = lookup_by_url("https://unknown.example/x")
    assert entry.slug == "generic"


def test_lookup_bestbuy_ca_beats_generic():
    entry = lookup_by_url("https://www.bestbuy.ca/en-ca/product/foo/12345")
    assert entry.slug == "bestbuy_ca"


def test_lookup_shop_subdomain_bestbuy_ca():
    entry = lookup_by_url("https://shop.bestbuy.ca/en-ca/product/foo/12345")
    assert entry.slug == "bestbuy_ca"


def test_lookup_fixture_url_by_retailer_slug():
    entry = lookup_by_url("https://fixtures.local/bestbuy_ca/in_stock")
    assert entry.slug == "bestbuy_ca"


def test_lookup_fixture_url_falls_back_to_generic():
    entry = lookup_by_url("https://fixtures.local/generic/jsonld_friendly")
    assert entry.slug == "generic"


def test_scraper_error_carries_context():
    err = RetailerNotSupportedError(
        "no match",
        retailer_slug="bestbuy_ca",
        url="https://example.test/p",
    )
    assert err.retailer_slug == "bestbuy_ca"
    assert err.url == "https://example.test/p"


def test_get_unknown_slug_raises():
    with pytest.raises(RetailerNotSupportedError, match="not registered"):
        get("no_such_retailer")


def test_duplicate_registration_raises():
    with pytest.raises(RetailerAlreadyRegisteredError):
        register(
            RetailerEntry(
                slug=EXAMPLE_RETAILER_SLUG,
                domains=("example-retailer.test",),
                default_category="tech",
                scrape=_example_scrape,
                default_strategy=ScrapeSource.FIXTURE,
            )
        )
