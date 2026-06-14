"""Tests for the generic JSON-LD/OG scraper."""

from __future__ import annotations

import pytest

from scrapers.exceptions import (
    FixtureNotFoundError,
    NotCanadianListingError,
    ScrapeBlockedError,
    ScrapeParseError,
)
from scrapers.extraction.jsonld import extract_jsonld
from scrapers.extraction.opengraph import extract_opengraph
from scrapers.extraction.price import normalize_currency, parse_price_cents
from scrapers.fixture_url import resolve_fixture_scenario
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret
from scrapers.generic import scrape
from scrapers.structured_data import extract_from_html

_JSONLD_PRODUCT_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Test Widget",
  "brand": "Acme",
  "image": "https://cdn.test/img.jpg",
  "offers": {
    "@type": "Offer",
    "price": "29.99",
    "priceCurrency": "CAD",
    "availability": "https://schema.org/InStock"
  }
}
</script></head></html>
"""

_JSONLD_GRAPH_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {"@type": "WebPage", "name": "Page"},
    {
      "@type": "Product",
      "name": "Graph Widget",
      "offers": {
        "@type": "Offer",
        "price": "15.00",
        "priceCurrency": "CAD",
        "availability": "https://schema.org/InStock"
      }
    }
  ]
}
</script></head></html>
"""

_OG_ONLY_HTML = """
<html><head>
<meta property="og:title" content="OG Shirt">
<meta property="og:image" content="https://cdn.test/shirt.jpg">
<meta property="og:price:amount" content="39.99">
<meta property="og:price:currency" content="CAD">
<meta property="product:availability" content="instock">
</head></html>
"""

_OUT_OF_STOCK_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@type": "Product",
  "name": "Sold Out Item",
  "offers": {
    "price": "10.00",
    "priceCurrency": "CAD",
    "availability": "https://schema.org/OutOfStock"
  }
}
</script></head></html>
"""

_USD_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@type": "Product",
  "name": "US Item",
  "offers": {"price": "9.99", "priceCurrency": "USD"}
}
</script></head></html>
"""

_NO_TITLE_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@type": "Product",
  "offers": {"price": "12.00", "priceCurrency": "CAD"}
}
</script></head></html>
"""

_JSONLD_TYPE_LIST_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@type": ["Thing", "Product"],
  "name": "Typed List Widget",
  "offers": {"price": "18.00", "priceCurrency": "CAD"}
}
</script></head></html>
"""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("29.99", 2999),
        ("$29.99", 2999),
        ("1,299.99", 129999),
    ],
)
def test_parse_price_cents(raw: str, expected: int) -> None:
    assert parse_price_cents(raw) == expected


def test_normalize_currency() -> None:
    assert normalize_currency("cad") == "CAD"
    assert normalize_currency(" USD ") == "USD"
    assert normalize_currency("dollar") is None


def test_jsonld_product_extracts_all_fields() -> None:
    extracted = extract_jsonld(_JSONLD_PRODUCT_HTML)
    assert extracted is not None
    assert extracted.title == "Test Widget"
    assert extracted.brand == "Acme"
    assert extracted.image_url == "https://cdn.test/img.jpg"
    assert extracted.price_cents == 2999
    assert extracted.currency == "CAD"
    assert extracted.is_in_stock is True
    assert extracted.raw_snapshot["extraction"] == "jsonld"


def test_jsonld_graph_product() -> None:
    extracted = extract_jsonld(_JSONLD_GRAPH_HTML)
    assert extracted is not None
    assert extracted.title == "Graph Widget"
    assert extracted.price_cents == 1500
    assert extracted.currency == "CAD"


def test_opengraph_extracts_fields() -> None:
    extracted = extract_opengraph(_OG_ONLY_HTML)
    assert extracted.title == "OG Shirt"
    assert extracted.image_url == "https://cdn.test/shirt.jpg"
    assert extracted.price_cents == 3999
    assert extracted.currency == "CAD"
    assert extracted.is_in_stock is True
    assert extracted.raw_snapshot["extraction"] == "opengraph"


def test_extract_from_html_og_fallback_when_no_jsonld() -> None:
    extracted = extract_from_html(_OG_ONLY_HTML)
    assert extracted.price_cents == 3999
    assert extracted.raw_snapshot["extraction"] == "opengraph"


def test_out_of_stock_jsonld() -> None:
    extracted = extract_jsonld(_OUT_OF_STOCK_HTML)
    assert extracted is not None
    assert extracted.is_in_stock is False


def test_usd_raises_not_canadian_listing_error() -> None:
    with pytest.raises(NotCanadianListingError) as exc_info:
        scrape("https://fixtures.local/generic/non_cad")
    assert (
        str(exc_info.value)
        == "This product appears to be priced in USD. V1 only supports Canadian listings."
    )


def test_no_price_raises_scrape_blocked_error() -> None:
    with pytest.raises(ScrapeBlockedError, match="Couldn't read price from this site"):
        scrape("https://fixtures.local/generic/no_extractable_data")


def test_resolve_fixture_scenario() -> None:
    assert resolve_fixture_scenario(
        "https://fixtures.local/generic/jsonld_friendly", "generic"
    ) == "jsonld_friendly"


def test_resolve_fixture_scenario_invalid_host() -> None:
    with pytest.raises(FixtureNotFoundError):
        resolve_fixture_scenario("https://example.test/generic/jsonld_friendly", "generic")


def test_resolve_fixture_scenario_invalid_path() -> None:
    with pytest.raises(FixtureNotFoundError):
        resolve_fixture_scenario("https://fixtures.local/generic", "generic")


def test_no_title_raises_scrape_parse_error() -> None:
    with pytest.raises(ScrapeParseError, match="Couldn't read product title from this site"):
        scrape("https://fixtures.local/generic/no_title")


def test_jsonld_type_list_product() -> None:
    extracted = extract_jsonld(_JSONLD_TYPE_LIST_HTML)
    assert extracted is not None
    assert extracted.title == "Typed List Widget"
    assert extracted.price_cents == 1800


def test_scrape_jsonld_friendly_fixture() -> None:
    snapshot = scrape("https://fixtures.local/generic/jsonld_friendly")
    assert snapshot.title == "Wireless Earbuds Pro"
    assert snapshot.brand == "SoundMax"
    assert snapshot.current_price_cents == 8999
    assert snapshot.currency_seen == "CAD"
    assert snapshot.is_in_stock is True
    assert snapshot.source.value == "fixture"
    assert snapshot.raw_snapshot["extraction"] == "jsonld"


def test_scrape_og_only_fixture() -> None:
    snapshot = scrape("https://fixtures.local/generic/og_only")
    assert snapshot.title == "Canvas Tote Bag"
    assert snapshot.current_price_cents == 2450
    assert snapshot.raw_snapshot["extraction"] == "opengraph"


def test_scrape_in_stock_fixture() -> None:
    snapshot = scrape("https://fixtures.local/generic/in_stock")
    assert snapshot.is_in_stock is True


def test_scrape_out_of_stock_fixture() -> None:
    snapshot = scrape("https://fixtures.local/generic/out_of_stock")
    assert snapshot.is_in_stock is False


def test_scrape_multi_variant_fixture() -> None:
    snapshot = scrape("https://fixtures.local/generic/multi_variant")
    assert len(snapshot.available_variants) >= 2


def test_usd_extract_from_html_direct() -> None:
    extracted = extract_from_html(_USD_HTML)
    assert extracted.currency == "USD"
    assert extracted.price_cents == 999


def test_fixture_loader_loads_generic_scenarios() -> None:
    loader = FixtureLoader()
    for scenario in (
        "jsonld_friendly",
        "og_only",
        "no_extractable_data",
        "in_stock",
        "out_of_stock",
        "multi_variant",
    ):
        assert loader.exists("generic", scenario)
