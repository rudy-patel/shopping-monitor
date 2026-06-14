"""Tests for Amazon.ca extraction and first-party rule."""

from __future__ import annotations

import pytest

from scrapers.extraction.amazon import (
    assert_amazon_ca_first_party,
    extract_amazon_html,
    is_amazon_ca_first_party,
)
from scrapers.exceptions import ScrapeBlockedError


def test_first_party_markers():
    html = '<div>Sold by: </span> <span class="a-size-small"> Amazon.ca </span></div>'
    assert is_amazon_ca_first_party(html) is True


def test_ships_from_and_sold_by_marker():
    html = "<div>Ships from and sold by Amazon.ca.</div>"
    assert is_amazon_ca_first_party(html) is True


def test_third_party_rejected():
    html = (
        '<div>Sold by: </span> <span class="a-size-small"> '
        "Acme Marketplace Inc. </span></div>"
    )
    with pytest.raises(ScrapeBlockedError, match="not sold directly by Amazon.ca"):
        assert_amazon_ca_first_party(html, url="https://www.amazon.ca/dp/B000000000")


def test_unavailable_without_seller_allowed():
    html = (
        '<div id="availability"><span>Currently unavailable.</span></div>'
        '<span id="productTitle">Example</span>'
    )
    assert_amazon_ca_first_party(html, url="https://www.amazon.ca/dp/B000000000") is None


def test_marketplace_anchor_seller_rejected():
    html = (
        '<span id="productTitle">AirPods Pro</span>'
        '<span class="a-price-whole">100</span><span class="a-price-fraction">00</span>'
        '<div id="availability"><span>In Stock</span></div>'
        'Sold by <a id="sellerProfileTriggerId">Third Party Seller</a>'
    )
    with pytest.raises(ScrapeBlockedError, match="not sold directly by Amazon.ca"):
        assert_amazon_ca_first_party(html, url="https://www.amazon.ca/dp/B000000000")


def test_unverified_buyable_listing_rejected():
    html = (
        '<span id="productTitle">Mystery Product</span>'
        '<span class="a-price-whole">50</span><span class="a-price-fraction">00</span>'
        '<div id="availability"><span>In Stock</span></div>'
    )
    with pytest.raises(ScrapeBlockedError, match="Could not verify"):
        assert_amazon_ca_first_party(html, url="https://www.amazon.ca/dp/B000000000")


def test_extract_from_recorded_in_stock_fixture():
    from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret

    html = FixtureLoader().load_text("amazon_ca", "in_stock")
    extracted = extract_amazon_html(
        html,
        "https://www.amazon.ca/Echo-Dot-5th-Gen-2022-release/dp/B09B8V1LZ3",
    )
    assert extracted.title
    assert "Echo Dot" in extracted.title
    assert extracted.price_cents == 6999
    assert extracted.is_in_stock is True
    assert len(extracted.available_variants) >= 2


def test_extract_out_of_stock_fixture():
    from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret

    html = FixtureLoader().load_text("amazon_ca", "out_of_stock")
    extracted = extract_amazon_html(
        html,
        "https://www.amazon.ca/Echo-Dot-5th-Gen-2022-release/dp/B09B8V1LZ3",
    )
    assert extracted.is_in_stock is False
    assert extracted.price_cents == 6999
