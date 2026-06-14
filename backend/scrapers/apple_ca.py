"""Apple Canada retailer scraper (PRD §11, T5.3)."""

from __future__ import annotations

from scrapers.extraction.apple import extract_apple_html
from scrapers.structured_retailer import make_structured_scraper, register_structured_retailer

_SLUG = "apple_ca"
_DOMAINS = ("apple.com", "www.apple.com")

scrape = make_structured_scraper(
    slug=_SLUG,
    domains=_DOMAINS,
    default_category="tech",
    parser=extract_apple_html,
)


def register_apple_ca() -> None:
    register_structured_retailer(
        slug=_SLUG,
        domains=_DOMAINS,
        default_category="tech",
        parser=extract_apple_html,
    )
