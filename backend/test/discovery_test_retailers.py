"""Test-only retailer scrapers for discovery unit tests."""

from __future__ import annotations

from scrapers.contract import ProductSnapshot, ScrapeSource, utc_now
from scrapers.exceptions import RetailerAlreadyRegisteredError
from scrapers.fixture_url import resolve_fixture_scenario
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret
from scrapers.registry import RetailerEntry, register
from scrapers.structured_data import extract_from_html


def _scrape_fixture_retailer(slug: str, url: str) -> ProductSnapshot:
    scenario = resolve_fixture_scenario(url, slug)
    html = FixtureLoader().load_text(slug, scenario)
    extracted = extract_from_html(html)
    return ProductSnapshot(
        retailer_slug=slug,
        url=url,
        title=extracted.title or "Unknown product",
        brand=extracted.brand,
        image_url=extracted.image_url,
        current_price_cents=extracted.price_cents or 0,
        currency_seen=extracted.currency or "CAD",
        is_in_stock=extracted.is_in_stock if extracted.is_in_stock is not None else True,
        available_variants=extracted.available_variants,
        selected_variant=extracted.selected_variant,
        breadcrumbs=extracted.breadcrumbs,
        scraped_at=utc_now(),
        source=ScrapeSource.FIXTURE,
        raw_snapshot=extracted.raw_snapshot,
    )


def _register(slug: str, domain: str) -> None:
    try:
        register(
            RetailerEntry(
                slug=slug,
                domains=(domain, f"www.{domain}"),
                default_category="tech",
                scrape=lambda url, s=slug: _scrape_fixture_retailer(s, url),
                default_strategy=ScrapeSource.FIXTURE,
                fixture_dir=slug,
            )
        )
    except RetailerAlreadyRegisteredError:
        pass


def register_discovery_test_retailers() -> None:
    """Register discovery_a / discovery_b / discovery_c / discovery_d test retailers (test-only)."""
    _register("discovery_a", "discovery-a.test")
    _register("discovery_b", "discovery-b.test")
    _register("discovery_c", "discovery-c.test")
    _register("discovery_d", "discovery-d.test")
