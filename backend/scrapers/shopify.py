"""Shared Shopify retailer scraper factory (T5.2)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from scrapers.contract import ProductSnapshot, ScrapeSource, utc_now
from scrapers.exceptions import (
    NotCanadianListingError,
    RetailerAlreadyRegisteredError,
    ScrapeBlockedError,
    ScrapeParseError,
)
from scrapers.extraction.shopify import merge_shopify_extraction
from scrapers.fixture_url import resolve_fixture_scenario
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret
from scrapers.http import scraper_fetch
from scrapers.mode import is_fixtures_mode  # pragma: allowlist secret
from scrapers.registry import RetailerEntry, register

CategorySlug = Literal["clothing", "shoes", "home", "tech", "other"]


def make_shopify_scraper(
    *,
    slug: str,
    domains: tuple[str, ...],
    default_category: CategorySlug,
) -> Callable[[str], ProductSnapshot]:
    """Build ``scrape(url)`` for a Shopify store using JSON-LD + theme meta."""

    def scrape(url: str) -> ProductSnapshot:
        if is_fixtures_mode():  # pragma: allowlist secret
            scenario = resolve_fixture_scenario(url, slug)
            html = FixtureLoader().load_text(slug, scenario)
            source = ScrapeSource.FIXTURE
        else:
            response = scraper_fetch(url, retailer_slug=slug)
            html = response.body_text
            source = ScrapeSource.STRUCTURED_DATA

        extracted = merge_shopify_extraction(html, url=url)

        if extracted.currency and extracted.currency != "CAD":
            raise NotCanadianListingError(
                f"This product appears to be priced in {extracted.currency}. "
                "V1 only supports Canadian listings.",
                retailer_slug=slug,
                url=url,
            )

        if extracted.price_cents is None:
            raise ScrapeBlockedError(
                "Couldn't read price from this site",
                retailer_slug=slug,
                url=url,
            )

        if not extracted.title:
            raise ScrapeParseError(
                "Couldn't read product title from this site",
                retailer_slug=slug,
                url=url,
            )

        return ProductSnapshot(
            retailer_slug=slug,
            url=url,
            title=extracted.title,
            brand=extracted.brand,
            image_url=extracted.image_url,
            current_price_cents=extracted.price_cents,
            currency_seen=extracted.currency or "CAD",
            is_in_stock=(
                extracted.is_in_stock if extracted.is_in_stock is not None else True
            ),
            available_variants=extracted.available_variants,
            selected_variant=extracted.selected_variant,
            breadcrumbs=extracted.breadcrumbs,
            scraped_at=utc_now(),
            source=source,
            raw_snapshot=extracted.raw_snapshot,
        )

    return scrape


def register_shopify_retailer(
    *,
    slug: str,
    domains: tuple[str, ...],
    default_category: CategorySlug,
) -> None:
    """Register a Shopify retailer (idempotent; safe after ``reset_registry()``)."""
    scrape = make_shopify_scraper(
        slug=slug,
        domains=domains,
        default_category=default_category,
    )
    try:
        register(
            RetailerEntry(
                slug=slug,
                domains=domains,
                default_category=default_category,
                scrape=scrape,
                default_strategy=ScrapeSource.STRUCTURED_DATA,
            )
        )
    except RetailerAlreadyRegisteredError:
        pass
