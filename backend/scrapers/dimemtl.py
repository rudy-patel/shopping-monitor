"""DIME MTL Shopify retailer scraper (PRD §11, T3.1b)."""

from __future__ import annotations

from scrapers.contract import ProductSnapshot, ScrapeSource, utc_now
from scrapers.exceptions import (
    NotCanadianListingError,
    RetailerAlreadyRegisteredError,
    ScrapeBlockedError,
    ScrapeParseError,
)
from scrapers.fixture_url import resolve_fixture_scenario
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret
from scrapers.http import scraper_fetch
from scrapers.mode import is_fixtures_mode  # pragma: allowlist secret
from scrapers.registry import RetailerEntry, register
from scrapers.structured_data import extract_from_html


def scrape(url: str) -> ProductSnapshot:
    if is_fixtures_mode():  # pragma: allowlist secret
        scenario = resolve_fixture_scenario(url, "dimemtl")
        html = FixtureLoader().load_text("dimemtl", scenario)
        source = ScrapeSource.FIXTURE
    else:
        response = scraper_fetch(url, retailer_slug="dimemtl")
        html = response.body_text
        source = ScrapeSource.STRUCTURED_DATA

    extracted = extract_from_html(html)

    if extracted.currency and extracted.currency != "CAD":
        raise NotCanadianListingError(
            f"This product appears to be priced in {extracted.currency}. "
            "V1 only supports Canadian listings.",
            retailer_slug="dimemtl",
            url=url,
        )

    if extracted.price_cents is None:
        raise ScrapeBlockedError(
            "Couldn't read price from this site",
            retailer_slug="dimemtl",
            url=url,
        )

    if not extracted.title:
        raise ScrapeParseError(
            "Couldn't read product title from this site",
            retailer_slug="dimemtl",
            url=url,
        )

    return ProductSnapshot(
        retailer_slug="dimemtl",
        url=url,
        title=extracted.title,
        brand=extracted.brand,
        image_url=extracted.image_url,
        current_price_cents=extracted.price_cents,
        currency_seen=extracted.currency or "CAD",
        is_in_stock=extracted.is_in_stock if extracted.is_in_stock is not None else True,
        available_variants=extracted.available_variants,
        selected_variant=extracted.selected_variant,
        breadcrumbs=extracted.breadcrumbs,
        scraped_at=utc_now(),
        source=source,
        raw_snapshot=extracted.raw_snapshot,
    )


def register_dimemtl() -> None:
    """Register DIME MTL (idempotent; safe after ``reset_registry()``)."""
    try:
        register(
            RetailerEntry(
                slug="dimemtl",
                domains=("dimemtl.com", "www.dimemtl.com"),
                default_category="clothing",
                scrape=scrape,
                default_strategy=ScrapeSource.STRUCTURED_DATA,
            )
        )
    except RetailerAlreadyRegisteredError:
        pass
