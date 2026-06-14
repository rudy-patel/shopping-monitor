"""HTTP-only bot-protected retailer scraper factory (T5.4).

Live mode tries ``scraper_fetch`` (``curl_cffi``) then optional retailer API probes.
Playwright is intentionally excluded from production scrapers per V1 deployment policy.
"""

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
from scrapers.extraction.types import ExtractedFields
from scrapers.fixture_url import resolve_fixture_scenario
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret
from scrapers.http import scraper_fetch
from scrapers.mode import is_fixtures_mode  # pragma: allowlist secret
from scrapers.registry import RetailerEntry, register

CategorySlug = Literal["clothing", "shoes", "home", "tech", "other"]
ParserFn = Callable[[str, str], ExtractedFields]
PostValidateFn = Callable[[ExtractedFields, str, str], None]
ApiProbeFn = Callable[[str], ExtractedFields]


def _snapshot_from_extracted(
    *,
    slug: str,
    url: str,
    extracted: ExtractedFields,
    source: ScrapeSource,
) -> ProductSnapshot:
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
        breadcrumbs=extracted.breadcrumbs or [],
        scraped_at=utc_now(),
        source=source,
        raw_snapshot=extracted.raw_snapshot,
    )


def make_bot_protected_scraper(
    *,
    slug: str,
    domains: tuple[str, ...],
    default_category: CategorySlug,
    parser: ParserFn,
    api_probe: ApiProbeFn | None = None,
    post_validate: PostValidateFn | None = None,
) -> Callable[[str], ProductSnapshot]:
    """Build ``scrape(url)`` with structured-data first and optional API fallback."""

    def scrape(url: str) -> ProductSnapshot:
        if is_fixtures_mode():  # pragma: allowlist secret
            scenario = resolve_fixture_scenario(url, slug)
            html = FixtureLoader().load_text(slug, scenario)
            extracted = parser(html, url)
            if post_validate is not None:
                post_validate(extracted, html, url)
            return _snapshot_from_extracted(
                slug=slug,
                url=url,
                extracted=extracted,
                source=ScrapeSource.FIXTURE,
            )

        source = ScrapeSource.STRUCTURED_DATA
        extracted: ExtractedFields | None = None
        html = ""

        try:
            response = scraper_fetch(url, retailer_slug=slug)
            html = response.body_text
            extracted = parser(html, url)
        except ScrapeBlockedError:
            extracted = None

        if extracted is None or extracted.price_cents is None:
            if api_probe is not None:
                extracted = api_probe(url)
                source = ScrapeSource.HTTP_PARSE
            elif extracted is None:
                raise ScrapeBlockedError(
                    "Retailer returned a blocked or challenge response",
                    retailer_slug=slug,
                    url=url,
                )

        if extracted.price_cents is None:
            raise ScrapeBlockedError(
                "Couldn't read price from this site",
                retailer_slug=slug,
                url=url,
            )

        if post_validate is not None:
            post_validate(extracted, html, url)

        return _snapshot_from_extracted(
            slug=slug,
            url=url,
            extracted=extracted,
            source=source,
        )

    return scrape


def register_bot_protected_retailer(
    *,
    slug: str,
    domains: tuple[str, ...],
    default_category: CategorySlug,
    parser: ParserFn,
    default_strategy: ScrapeSource = ScrapeSource.STRUCTURED_DATA,
    fallback_strategies: tuple[ScrapeSource, ...] = (),
    api_probe: ApiProbeFn | None = None,
    post_validate: PostValidateFn | None = None,
) -> None:
    """Register a bot-protected retailer (idempotent)."""
    scrape = make_bot_protected_scraper(
        slug=slug,
        domains=domains,
        default_category=default_category,
        parser=parser,
        api_probe=api_probe,
        post_validate=post_validate,
    )
    try:
        register(
            RetailerEntry(
                slug=slug,
                domains=domains,
                default_category=default_category,
                scrape=scrape,
                default_strategy=default_strategy,
                fallback_strategies=fallback_strategies,
            )
        )
    except RetailerAlreadyRegisteredError:
        pass
