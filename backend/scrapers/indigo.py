"""Indigo (Shopify) retailer scraper (PRD §11, T5.3)."""

from __future__ import annotations

from scrapers.extraction.indigo import merge_indigo_extraction
from scrapers.structured_retailer import make_structured_scraper, register_structured_retailer

_SLUG = "indigo"
_DOMAINS = ("indigo.ca", "www.indigo.ca")

scrape = make_structured_scraper(
    slug=_SLUG,
    domains=_DOMAINS,
    default_category="other",
    parser=merge_indigo_extraction,
)


def register_indigo() -> None:
    register_structured_retailer(
        slug=_SLUG,
        domains=_DOMAINS,
        default_category="other",
        parser=merge_indigo_extraction,
    )
