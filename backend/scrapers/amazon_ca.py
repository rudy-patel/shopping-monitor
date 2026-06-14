"""Amazon.ca retailer scraper (PRD §11, T5.4)."""

from __future__ import annotations

from scrapers.bot_protected_retailer import (
    make_bot_protected_scraper,
    register_bot_protected_retailer,
)
from scrapers.extraction.amazon import extract_amazon_html, validate_amazon_listing

_SLUG = "amazon_ca"
_DOMAINS = ("amazon.ca", "www.amazon.ca")

scrape = make_bot_protected_scraper(
    slug=_SLUG,
    domains=_DOMAINS,
    default_category="other",
    parser=extract_amazon_html,
    post_validate=validate_amazon_listing,
)


def register_amazon_ca() -> None:
    register_bot_protected_retailer(
        slug=_SLUG,
        domains=_DOMAINS,
        default_category="other",
        parser=extract_amazon_html,
        post_validate=validate_amazon_listing,
    )
