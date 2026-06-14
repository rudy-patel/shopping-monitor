"""Abercrombie & Fitch Canada retailer scraper (PRD §11, T5.3)."""

from __future__ import annotations

from scrapers.extraction.abercrombie import extract_abercrombie_html
from scrapers.structured_retailer import make_structured_scraper, register_structured_retailer

_SLUG = "abercrombie"
_DOMAINS = ("abercrombie.com", "www.abercrombie.com")

scrape = make_structured_scraper(
    slug=_SLUG,
    domains=_DOMAINS,
    default_category="clothing",
    parser=extract_abercrombie_html,
)


def register_abercrombie() -> None:
    register_structured_retailer(
        slug=_SLUG,
        domains=_DOMAINS,
        default_category="clothing",
        parser=extract_abercrombie_html,
    )
