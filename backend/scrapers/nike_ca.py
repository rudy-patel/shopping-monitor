"""Nike Canada retailer scraper (PRD §11, T5.4)."""

from __future__ import annotations

from scrapers.bot_protected_retailer import (
    make_bot_protected_scraper,
    register_bot_protected_retailer,
)
from scrapers.extraction.nike import extract_nike_html

_SLUG = "nike_ca"
_DOMAINS = ("nike.com", "www.nike.com")

scrape = make_bot_protected_scraper(
    slug=_SLUG,
    domains=_DOMAINS,
    default_category="shoes",
    parser=extract_nike_html,
)


def register_nike_ca() -> None:
    register_bot_protected_retailer(
        slug=_SLUG,
        domains=_DOMAINS,
        default_category="shoes",
        parser=extract_nike_html,
    )
