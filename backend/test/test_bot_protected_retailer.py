"""Tests for bot-protected retailer factory."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from scrapers.bot_protected_retailer import make_bot_protected_scraper
from scrapers.contract import ScrapeSource
from scrapers.exceptions import ScrapeBlockedError
from scrapers.extraction.types import ExtractedFields
from scrapers.http import ScraperResponse


def _fields(**overrides) -> ExtractedFields:
    base = ExtractedFields(
        title="Sample Product",
        price_cents=1999,
        currency="CAD",
        is_in_stock=True,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_live_mode_uses_structured_data_when_parser_succeeds():
    scrape = make_bot_protected_scraper(
        slug="amazon_ca",
        domains=("amazon.ca",),
        default_category="other",
        parser=lambda _html, _url: _fields(),
    )

    response = ScraperResponse(
        status_code=200,
        body_text="<html></html>",
        body_bytes=b"",
        headers={},
        final_url="https://www.amazon.ca/dp/B000000000",
    )

    with (
        patch("scrapers.bot_protected_retailer.is_fixtures_mode", return_value=False),
        patch("scrapers.bot_protected_retailer.scraper_fetch", return_value=response),
    ):
        snapshot = scrape("https://www.amazon.ca/dp/B000000000")

    assert snapshot.source == ScrapeSource.STRUCTURED_DATA
    assert snapshot.current_price_cents == 1999


def test_live_mode_falls_back_to_api_probe():
    def parser(_html: str, _url: str) -> ExtractedFields:
        return _fields(price_cents=None)

    def probe(_url: str) -> ExtractedFields:
        return _fields(title="From API", price_cents=2500)

    scrape = make_bot_protected_scraper(
        slug="amazon_ca",
        domains=("amazon.ca",),
        default_category="other",
        parser=parser,
        api_probe=probe,
    )

    response = ScraperResponse(
        status_code=200,
        body_text="<html></html>",
        body_bytes=b"",
        headers={},
        final_url="https://www.amazon.ca/dp/B000000000",
    )

    with (
        patch("scrapers.bot_protected_retailer.is_fixtures_mode", return_value=False),
        patch("scrapers.bot_protected_retailer.scraper_fetch", return_value=response),
    ):
        snapshot = scrape("https://www.amazon.ca/dp/B000000000")

    assert snapshot.source == ScrapeSource.HTTP_PARSE
    assert snapshot.title == "From API"


def test_live_mode_raises_when_blocked_and_no_probe():
    def parser(_html: str, _url: str) -> ExtractedFields:
        raise ScrapeBlockedError("blocked", retailer_slug="amazon_ca")

    scrape = make_bot_protected_scraper(
        slug="amazon_ca",
        domains=("amazon.ca",),
        default_category="other",
        parser=parser,
    )

    with (
        patch("scrapers.bot_protected_retailer.is_fixtures_mode", return_value=False),
        patch(
            "scrapers.bot_protected_retailer.scraper_fetch",
            side_effect=ScrapeBlockedError("blocked", retailer_slug="amazon_ca"),
        ),
        pytest.raises(ScrapeBlockedError),
    ):
        scrape("https://www.amazon.ca/dp/B000000000")
