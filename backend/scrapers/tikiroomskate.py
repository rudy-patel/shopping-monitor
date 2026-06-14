"""Tiki Room Skateboards Shopify retailer scraper (PRD §11, T5.2)."""

from __future__ import annotations

from scrapers.shopify import make_shopify_scraper, register_shopify_retailer

_SLUG = "tikiroomskate"
_DOMAINS = ("tikiroomskateboards.com", "www.tikiroomskateboards.com")

scrape = make_shopify_scraper(slug=_SLUG, domains=_DOMAINS, default_category="other")


def register_tikiroomskate() -> None:
    register_shopify_retailer(slug=_SLUG, domains=_DOMAINS, default_category="other")
