"""Best Buy Canada retailer scraper."""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

from scrapers.contract import (
    ProductSnapshot,
    ScrapeSource,
    VariantAttribute,
    VariantCombination,
    utc_now,
)
from scrapers.exceptions import (
    NotCanadianListingError,
    RetailerAlreadyRegisteredError,
    ScrapeBlockedError,
    ScrapeParseError,
)
from scrapers.extraction.bestbuy import extract_bestbuy_embedded
from scrapers.extraction.bestbuy_api import extract_from_product_url_via_api, product_id_from_url
from scrapers.extraction.jsonld import collect_schema_types
from scrapers.extraction.types import ExtractedFields
from scrapers.fixture_url import resolve_fixture_scenario
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret
from scrapers.http import scraper_fetch
from scrapers.mode import is_fixtures_mode  # pragma: allowlist secret
from scrapers.registry import RetailerEntry, register
from scrapers.structured_data import extract_from_html


def _resolve_selected_variant(
    url: str,
    available_variants: list[VariantCombination],
) -> list[VariantAttribute] | None:
    sku = (parse_qs(urlsplit(url).query).get("sku") or [None])[0]
    if sku:
        for variant in available_variants:
            if variant.sku == sku:
                return variant.attributes
    if len(available_variants) == 1:
        return available_variants[0].attributes
    return None


def extract_bestbuy_html(html: str, *, url: str) -> ExtractedFields:
    """Extract Best Buy product fields from JSON-LD/OG plus embedded state."""
    extracted = extract_from_html(html)
    embedded = extract_bestbuy_embedded(html)

    if embedded is not None:
        if embedded.is_in_stock is not None:
            extracted.is_in_stock = embedded.is_in_stock
        if embedded.available_variants:
            extracted.available_variants = embedded.available_variants
        if embedded.raw_snapshot.get("sku"):
            extracted.raw_snapshot["sku"] = embedded.raw_snapshot["sku"]

    schema_types = collect_schema_types(html)
    raw_snapshot = dict(extracted.raw_snapshot)
    raw_snapshot["schema_types"] = schema_types
    raw_snapshot["product_id"] = product_id_from_url(url) or raw_snapshot.get("sku")
    extracted.raw_snapshot = raw_snapshot
    extracted.selected_variant = _resolve_selected_variant(url, extracted.available_variants)
    return extracted


def _snapshot_from_extracted(
    *,
    url: str,
    extracted: ExtractedFields,
    source: ScrapeSource,
) -> ProductSnapshot:
    if extracted.currency and extracted.currency != "CAD":
        raise NotCanadianListingError(
            f"This product appears to be priced in {extracted.currency}. "
            "V1 only supports Canadian listings.",
            retailer_slug="bestbuy_ca",
            url=url,
        )

    if extracted.price_cents is None:
        raise ScrapeBlockedError(
            "Couldn't read price from this site",
            retailer_slug="bestbuy_ca",
            url=url,
        )

    if not extracted.title:
        raise ScrapeParseError(
            "Couldn't read product title from this site",
            retailer_slug="bestbuy_ca",
            url=url,
        )

    return ProductSnapshot(
        retailer_slug="bestbuy_ca",
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


def scrape(url: str) -> ProductSnapshot:
    if is_fixtures_mode():  # pragma: allowlist secret
        scenario = resolve_fixture_scenario(url, "bestbuy_ca")
        html = FixtureLoader().load_text("bestbuy_ca", scenario)
        extracted = extract_bestbuy_html(html, url=url)
        return _snapshot_from_extracted(
            url=url,
            extracted=extracted,
            source=ScrapeSource.FIXTURE,
        )

    source = ScrapeSource.STRUCTURED_DATA
    try:
        response = scraper_fetch(url, retailer_slug="bestbuy_ca")
        extracted = extract_bestbuy_html(response.body_text, url=url)
    except ScrapeBlockedError:
        extracted = extract_from_product_url_via_api(url)
        source = ScrapeSource.HTTP_PARSE
        return _snapshot_from_extracted(url=url, extracted=extracted, source=source)

    if extracted.price_cents is None:
        extracted = extract_from_product_url_via_api(url)
        source = ScrapeSource.HTTP_PARSE

    return _snapshot_from_extracted(url=url, extracted=extracted, source=source)


def register_bestbuy_ca() -> None:
    """Register Best Buy Canada (idempotent; safe after ``reset_registry()``)."""
    try:
        register(
            RetailerEntry(
                slug="bestbuy_ca",
                domains=("bestbuy.ca", "www.bestbuy.ca"),
                default_category="tech",
                scrape=scrape,
                default_strategy=ScrapeSource.STRUCTURED_DATA,
                fallback_strategies=(ScrapeSource.HTTP_PARSE,),
            )
        )
    except RetailerAlreadyRegisteredError:
        pass
