"""Retailer scraper contract, registry, and fixture harness."""

from scrapers.contract import (
    ProductSnapshot,
    ScrapeSource,
    VariantAttribute,
    VariantCombination,
)
from scrapers.exceptions import ScraperError
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret
from scrapers.http import ScraperResponse, scraper_fetch
from scrapers.mode import ScraperMode, get_scraper_mode, is_fixtures_mode  # pragma: allowlist secret
from scrapers.registry import RetailerEntry, all_retailers, get, lookup_by_url, register

__all__ = [
    "FixtureLoader",
    "ProductSnapshot",
    "RetailerEntry",
    "ScrapeSource",
    "ScraperError",
    "ScraperMode",
    "ScraperResponse",
    "VariantAttribute",
    "VariantCombination",
    "all_retailers",
    "get",
    "get_scraper_mode",
    "is_fixtures_mode",  # pragma: allowlist secret
    "lookup_by_url",
    "register",
    "scraper_fetch",
]
