"""Tests for structured retailer extraction helpers (T5.3)."""

from __future__ import annotations

from pathlib import Path

from scrapers.extraction.abercrombie import extract_abercrombie_html
from scrapers.extraction.apple import _is_buy_config_url, extract_apple_html
from scrapers.extraction.embedded_json import parse_price_from_formatted
from scrapers.extraction.indigo import merge_indigo_extraction

_FIXTURES = Path("test/fixtures/retailers")


def test_parse_price_from_formatted_handles_nbsp_cad():
    assert parse_price_from_formatted("$34.97&nbsp;CAD") == 3497


def test_indigo_out_of_stock_prefers_physical_format():
    html = (_FIXTURES / "indigo/out_of_stock.html").read_text()
    extracted = merge_indigo_extraction(
        html,
        "https://fixtures.local/indigo/out_of_stock",
    )
    assert extracted.is_in_stock is False
    assert extracted.price_cents is not None


def test_apple_config_url_detection():
    assert _is_buy_config_url(
        "https://www.apple.com/ca/shop/buy-iphone/iphone-16/6.1-inch-display-128gb-black"
    )
    assert not _is_buy_config_url(
        "https://www.apple.com/ca/shop/buy-iphone/iphone-16"
    )


def test_apple_config_page_uses_jsonld_stock_not_buy_grid():
    html = (_FIXTURES / "apple_ca/out_of_stock.html").read_text()
    config_url = (
        "https://www.apple.com/ca/shop/buy-iphone/iphone-16/"
        "6.1-inch-display-128gb-black"
    )
    extracted = extract_apple_html(html, config_url)
    assert extracted.is_in_stock is False
    assert len(extracted.available_variants) == 0


def test_abercrombie_stock_uses_primary_product_skus_only():
    html = (_FIXTURES / "abercrombie/in_stock.html").read_text()
    extracted = extract_abercrombie_html(
        html,
        "https://fixtures.local/abercrombie/in_stock",
    )
    assert extracted.is_in_stock is True
    assert extracted.price_cents == 3497
    assert any(variant.is_in_stock for variant in extracted.available_variants)
