"""Tests for the scraper benchmark harness (T5.1)."""

from __future__ import annotations

import json

from scrapers.benchmark.catalog import load_catalog
from scrapers.benchmark.fields import detect_blocked_markers
from scrapers.benchmark.runner import run_benchmark
from scrapers.benchmark.strategies import run_http_parse, run_playwright, run_structured_data
from scrapers.benchmark.types import BenchmarkReport, CatalogEntry, FieldExpect
from scrapers.exceptions import ScrapeBlockedError
from scrapers.extraction.bestbuy_api import extract_bestbuy_api_json
from scrapers.http import ScraperResponse

_SWITCH_2_PAYLOAD = {
    "name": "Nintendo Switch 2 Console",
    "sku": "19296507",
    "brandName": "NINTENDO",
    "salePrice": 629.99,
    "regularPrice": 629.99,
    "categoryName": "Nintendo Switch 2 Consoles",
    "thumbnailImage": "https://multimedia.bbycastatic.ca/multimedia/products/55x55/192/19296/19296507.jpg",
    "availability": {
        "onlineAvailability": "InStock",
        "isAvailableOnline": True,
    },
}


def _entry(slug: str, scenario: str, **expect_kwargs) -> CatalogEntry:
    expect = FieldExpect(**expect_kwargs) if expect_kwargs else FieldExpect()
    return CatalogEntry(
        slug=slug,
        scenario=scenario,
        url=f"https://fixtures.local/{slug}/{scenario}",
        expect=expect,
    )


def test_catalog_loads_twenty_five_entries():
    version, entries = load_catalog()
    assert version == "1"
    assert len(entries) == 25
    slugs = {entry.slug for entry in entries}
    assert slugs == {
        "generic",
        "bestbuy_ca",
        "palmisleskate",
        "tikiroomskate",
        "indigo",
        "apple_ca",
        "abercrombie",
        "amazon_ca",
        "nike_ca",
    }
    for entry in entries:
        assert entry.url.startswith("https://fixtures.local/")


def test_structured_data_bestbuy_in_stock():
    entry = _entry("bestbuy_ca", "in_stock")
    result = run_structured_data(entry, live=False, retries=0)
    assert result.status == "success"
    assert result.fields.title.ok
    assert result.fields.price.ok
    assert result.fields.stock.ok
    assert result.fields.image.ok


def test_structured_data_bestbuy_multi_variant():
    entry = _entry(
        "bestbuy_ca",
        "multi_variant",
        variants=True,
    )
    result = run_structured_data(entry, live=False, retries=0)
    assert result.status == "success"
    assert result.fields.variants.ok
    assert result.fields.variants.value >= 2


def test_structured_data_shopify_scenarios():
    _, entries = load_catalog(slugs=["palmisleskate", "tikiroomskate"])
    for entry in entries:
        result = run_structured_data(entry, live=False, retries=0)
        assert result.status == "success"
        assert result.fields.title.ok
        assert result.fields.price.ok
        assert result.fields.stock.ok


def test_structured_data_t53_retailers():
    _, entries = load_catalog(slugs=["indigo", "apple_ca", "abercrombie"])
    for entry in entries:
        result = run_structured_data(entry, live=False, retries=0)
        assert result.status == "success", f"{entry.slug}/{entry.scenario} failed"
        assert result.fields.title.ok
        assert result.fields.price.ok
        assert result.fields.stock.ok
        if entry.expect.variants:
            assert result.fields.variants.ok


def test_structured_data_t54_retailers():
    _, entries = load_catalog(slugs=["amazon_ca", "nike_ca"])
    for entry in entries:
        result = run_structured_data(entry, live=False, retries=0)
        assert result.status == "success", f"{entry.slug}/{entry.scenario} failed"
        assert result.fields.title.ok
        assert result.fields.price.ok
        assert result.fields.stock.ok
        if entry.expect.variants:
            assert result.fields.variants.ok


def test_structured_data_generic_jsonld_and_og():
    for scenario in ("jsonld_friendly", "og_only"):
        entry = _entry("generic", scenario)
        result = run_structured_data(entry, live=False, retries=0)
        assert result.status == "success"
        assert result.fields.title.ok
        assert result.fields.price.ok
        assert result.fields.stock.ok
        assert result.fields.image.ok


def test_http_parse_skipped_in_fixture_mode():
    entry = _entry("bestbuy_ca", "in_stock")
    result = run_http_parse(entry, live=False, retries=0)
    assert result.status == "skipped"
    assert result.reason == "skipped_in_fixture_mode"


def test_playwright_skipped_without_install(monkeypatch):
    monkeypatch.setattr(
        "scrapers.benchmark.playwright_fetch.playwright_available",
        lambda: False,
    )
    entry = _entry("generic", "jsonld_friendly")
    result = run_playwright(entry, live=True, with_playwright=True, retries=0)
    assert result.status == "skipped"
    assert result.reason == "playwright_not_installed"


def test_bestbuy_api_probe_called_when_html_blocked(monkeypatch):
    entry = CatalogEntry(
        slug="bestbuy_ca",
        scenario="api_fallback",
        url="https://www.bestbuy.ca/en-ca/product/nintendo-switch-2-console/19296507",
        expect=FieldExpect(),
    )

    def fake_fetch(url: str, *, retailer_slug: str, **kwargs):
        return ScraperResponse(
            status_code=403,
            body_text="Access Denied. Cloudflare protection.",
            body_bytes=b"Access Denied. Cloudflare protection.",
            headers={},
            final_url=url,
        )

    monkeypatch.setattr("scrapers.benchmark.strategies.scraper_fetch", fake_fetch)
    monkeypatch.setattr(
        "scrapers.extraction.bestbuy_api.fetch_product_payload",
        lambda product_id: _SWITCH_2_PAYLOAD,
    )

    result = run_http_parse(entry, live=True, retries=0)
    assert result.status == "success"
    assert len(result.http_parse_attempts) == 2
    assert result.http_parse_attempts[0].kind == "html"
    assert result.http_parse_attempts[0].status == "blocked"
    assert result.http_parse_attempts[1].kind == "retailer_api"
    assert result.http_parse_attempts[1].status == "success"
    assert result.http_parse_attempts[1].api == "bestbuy_json_v2"
    assert result.fields.title.ok
    assert result.fields.price.ok


def test_catalog_slug_filter():
    _, entries = load_catalog(slugs=["bestbuy_ca"])
    assert len(entries) == 2
    assert all(entry.slug == "bestbuy_ca" for entry in entries)


def test_playwright_not_requested():
    entry = _entry("generic", "jsonld_friendly")
    result = run_playwright(entry, live=False, with_playwright=False, retries=0)
    assert result.status == "skipped"
    assert result.reason == "playwright_not_requested"


def test_bestbuy_advisory_http_parse_fallback():
    report = run_benchmark()
    bestbuy = next(s for s in report.summaries if s.slug == "bestbuy_ca")
    assert bestbuy.fallback_strategies == ["http_parse"]
    assert "HTTP_PARSE" in bestbuy.registry_snippet


def test_report_summaries_cover_catalog_slugs():
    report = run_benchmark()
    assert len(report.summaries) == 9
    assert {summary.slug for summary in report.summaries} == {
        "generic",
        "bestbuy_ca",
        "palmisleskate",
        "tikiroomskate",
        "indigo",
        "apple_ca",
        "abercrombie",
        "amazon_ca",
        "nike_ca",
    }


def test_recommendation_bestbuy_prefers_structured_on_fixtures():
    report = run_benchmark()
    bestbuy = next(s for s in report.summaries if s.slug == "bestbuy_ca")
    assert bestbuy.default_strategy == "structured_data"


def test_output_serializes_to_json():
    report = run_benchmark()
    payload = report.model_dump(mode="json")
    round_trip = BenchmarkReport.model_validate(payload)
    assert round_trip.catalog_version == report.catalog_version
    assert len(round_trip.runs) == len(report.runs)
    assert json.dumps(payload)


def test_blocked_markers_on_403_response():
    body = "<html>Access Denied. Cloudflare ray ID abc</html>"
    markers = detect_blocked_markers(403, body)
    assert "403" in markers
    assert "access_denied" in markers
    assert "cloudflare" in markers


def test_scrape_blocked_error_triggers_api_probe(monkeypatch):
    entry = CatalogEntry(
        slug="bestbuy_ca",
        scenario="api_fallback",
        url="https://www.bestbuy.ca/en-ca/product/nintendo-switch-2-console/19296507",
        expect=FieldExpect(),
    )

    def raise_blocked(*args, **kwargs):
        raise ScrapeBlockedError("blocked", retailer_slug="bestbuy_ca", url=entry.url)

    monkeypatch.setattr("scrapers.benchmark.strategies.scraper_fetch", raise_blocked)
    monkeypatch.setattr(
        "scrapers.extraction.bestbuy_api.fetch_product_payload",
        lambda product_id: _SWITCH_2_PAYLOAD,
    )

    result = run_http_parse(entry, live=True, retries=0)
    assert result.http_parse_attempts[-1].kind == "retailer_api"
    assert result.http_parse_attempts[-1].status == "success"
    extracted = extract_bestbuy_api_json(_SWITCH_2_PAYLOAD)
    assert result.fields.price.value == extracted.price_cents
