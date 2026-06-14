"""Palm Isle Skate Shop Shopify retailer scraper (PRD §11, T5.2)."""

from __future__ import annotations

from scrapers.shopify import make_shopify_scraper, register_shopify_retailer

_SLUG = "palmisleskate"
_DOMAINS = ("palmisleskateshop.com", "www.palmisleskateshop.com")

scrape = make_shopify_scraper(slug=_SLUG, domains=_DOMAINS, default_category="other")


def register_palmisleskate() -> None:
    register_shopify_retailer(slug=_SLUG, domains=_DOMAINS, default_category="other")
