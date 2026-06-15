"""Tests for retailer drift detection (T5.5) — fixture-only, no live network."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

import scrapers.bootstrap  # noqa: F401
from scrapers.benchmark.catalog import load_catalog as load_benchmark_catalog
from scrapers.benchmark.types import FieldExpect
from scrapers.contract import ProductSnapshot, ScrapeSource, VariantAttribute, VariantCombination, utc_now
from scrapers.drift.catalog import load_catalog, snapshot_path
from scrapers.drift.compare import compare_to_baseline, fingerprint_diff, load_baseline, write_baseline
from scrapers.drift.github_issues import (
    GitHubIssueClient,
    GitHubRepo,
    format_issue_body,
    issue_title,
    resolve_github_repo,
)
from scrapers.drift.normalize import check_expect_fields, normalize, variant_count_bucket
from scrapers.drift.runner import run_drift_checks, scrape_fixture_baseline
from scrapers.drift.types import DriftCheckResult, DriftSnapshot
from scrapers.exceptions import ScrapeBlockedError, ScrapeParseError
from scrapers.registry import all_retailers, reset_registry
from test.production_registry import register_production_retailers

REPO_ROOT = Path(__file__).resolve().parents[2]


def _sample_snapshot(**overrides: Any) -> ProductSnapshot:
    payload: dict[str, Any] = {
        "retailer_slug": "palmisleskate",
        "url": "https://palmisleskateshop.com/products/bones-reds-bearings",
        "title": "Bones Reds Bearings",
        "brand": "Bones",
        "image_url": "https://cdn.test/bones.jpg",
        "current_price_cents": 2800,
        "currency_seen": "CAD",
        "is_in_stock": True,
        "available_variants": [],
        "selected_variant": None,
        "breadcrumbs": [],
        "scraped_at": utc_now(),
        "source": ScrapeSource.FIXTURE,
        "raw_snapshot": {"extraction": "jsonld"},
    }
    payload.update(overrides)
    return ProductSnapshot.model_validate(payload)


@pytest.fixture(autouse=True)
def production_registry():
    register_production_retailers()
    yield
    reset_registry()


def test_drift_catalog_covers_production_retailers_except_generic():
    _, entries = load_catalog()
    catalog_slugs = {entry.slug for entry in entries}
    production_slugs = {entry.slug for entry in all_retailers() if entry.slug != "generic"}
    assert catalog_slugs == production_slugs


def test_drift_catalog_expect_matches_benchmark_in_stock():
    _, drift_entries = load_catalog()
    _, benchmark_entries = load_benchmark_catalog()
    benchmark_by_key = {(entry.slug, entry.scenario): entry.expect for entry in benchmark_entries}
    for entry in drift_entries:
        assert entry.expect == benchmark_by_key[(entry.slug, entry.scenario)]


def test_drift_catalog_urls_are_live_not_fixtures_local():
    _, entries = load_catalog()
    for entry in entries:
        assert "fixtures.local" not in entry.url
        assert entry.url.startswith("https://")


def test_variant_count_bucket():
    assert variant_count_bucket(0) == "0"
    assert variant_count_bucket(1) == "1"
    assert variant_count_bucket(99) == "2+"


def test_normalize_ignores_volatile_fields():
    baseline = normalize(
        _sample_snapshot(
            title="Old title",
            current_price_cents=999,
            is_in_stock=False,
        )
    )
    live = normalize(
        _sample_snapshot(
            title="New title",
            current_price_cents=12345,
            is_in_stock=False,
            image_url="https://cdn.test/other.jpg",
        )
    )
    assert baseline == live


def test_normalize_tracks_variant_structure():
    snapshot = _sample_snapshot(
        available_variants=[
            VariantCombination(
                attributes=[
                    VariantAttribute(attribute_name="Size", attribute_value="M"),
                    VariantAttribute(attribute_name="Color", attribute_value="Red"),
                ]
            ),
            VariantCombination(
                attributes=[
                    VariantAttribute(attribute_name="Color", attribute_value="Blue"),
                    VariantAttribute(attribute_name="Size", attribute_value="L"),
                ]
            ),
        ],
        selected_variant=[VariantAttribute(attribute_name="Size", attribute_value="M")],
    )
    fingerprint = normalize(snapshot)
    assert fingerprint.variant_attribute_names == ["Color", "Size"]
    assert fingerprint.variant_count_bucket == "2+"
    assert fingerprint.selected_variant_attribute_names == ["Size"]


def test_check_expect_fields():
    snapshot = _sample_snapshot(image_url=None)
    failures = check_expect_fields(snapshot, FieldExpect(image=True, variants=False))
    assert failures == ["image"]


def test_normalize_canonicalizes_bestbuy_extraction():
    snapshot = _sample_snapshot(
        retailer_slug="bestbuy_ca",
        url="https://www.bestbuy.ca/en-ca/product/example/19220080",
        raw_snapshot={"extraction": "jsonld"},
    )
    assert normalize(snapshot).extraction == "bestbuy"
    api_snapshot = snapshot.model_copy(
        update={"raw_snapshot": {"extraction": "bestbuy_api"}}
    )
    assert normalize(api_snapshot).extraction == "bestbuy"


def test_fingerprint_diff_ignores_live_selected_variant_when_baseline_empty():
    baseline = DriftSnapshot(
        has_title=True,
        has_price=True,
        has_stock=True,
        has_image=True,
        has_variants=True,
        variant_attribute_names=["option_1", "option_2"],
        variant_count_bucket="2+",
        selected_variant_attribute_names=[],
    )
    live = baseline.model_copy(
        update={"selected_variant_attribute_names": ["option_1", "option_2"]}
    )
    assert fingerprint_diff(baseline, live) == {}


def test_fingerprint_diff_reports_changed_fields():
    baseline = DriftSnapshot(
        has_title=True,
        has_price=True,
        has_stock=True,
        has_image=True,
        has_variants=False,
        variant_count_bucket="0",
    )
    live = baseline.model_copy(update={"has_image": False, "extraction": "opengraph"})
    diff = fingerprint_diff(baseline, live)
    assert set(diff) == {"has_image", "extraction"}


def test_drift_snapshots_match_fixtures():
    _, entries = load_catalog()
    for entry in entries:
        snapshot = scrape_fixture_baseline(entry.slug, entry.scenario)
        expected = normalize(snapshot)
        committed = load_baseline(entry.slug)
        assert committed == expected, f"Drift baseline stale for {entry.slug}; run make update-drift-snapshots"


def test_compare_to_baseline_ok_for_fixture_scrape():
    entry = next(entry for entry in load_catalog()[1] if entry.slug == "palmisleskate")
    snapshot = scrape_fixture_baseline(entry.slug, entry.scenario)
    ok, diff, _, _, expect_failures = compare_to_baseline(
        slug=entry.slug,
        live_snapshot=snapshot,
        expect=entry.expect,
    )
    assert ok is True
    assert diff == {}
    assert expect_failures == []


def test_run_drift_checks_ok_with_mock_live_scrape():
    def mock_live(slug: str, url: str) -> ProductSnapshot:
        entry = next(item for item in load_catalog()[1] if item.slug == slug)
        return scrape_fixture_baseline(slug, entry.scenario)

    report = run_drift_checks(live_scrape_fn=mock_live)
    assert report.ok is True
    assert len(report.results) == 8
    assert all(result.status == "ok" for result in report.results)


def test_run_drift_checks_shape_mismatch_with_mock_live():
    palmisleskate = next(item for item in load_catalog()[1] if item.slug == "palmisleskate")
    baseline_snapshot = scrape_fixture_baseline("palmisleskate", palmisleskate.scenario)

    def mock_live(slug: str, url: str) -> ProductSnapshot:
        if slug == "palmisleskate":
            return baseline_snapshot.model_copy(
                update={"raw_snapshot": {"extraction": "opengraph"}},
            )
        entry = next(item for item in load_catalog()[1] if item.slug == slug)
        return scrape_fixture_baseline(slug, entry.scenario)

    report = run_drift_checks(slugs=["palmisleskate"], live_scrape_fn=mock_live)
    assert report.ok is False
    result = report.results[0]
    assert result.status == "shape_mismatch"
    assert result.diff
    assert "extraction" in result.diff


def test_run_drift_checks_blocked_with_mock_live():
    def mock_live(slug: str, url: str) -> ProductSnapshot:
        raise ScrapeBlockedError("Access denied", retailer_slug=slug, url=url)

    report = run_drift_checks(slugs=["nike_ca"], live_scrape_fn=mock_live)
    assert report.ok is False
    assert report.results[0].status == "blocked"


def test_run_drift_checks_error_with_mock_live():
    def mock_live(slug: str, url: str) -> ProductSnapshot:
        raise ScrapeParseError("parse failed", retailer_slug=slug, url=url)

    report = run_drift_checks(slugs=["amazon_ca"], live_scrape_fn=mock_live)
    assert report.ok is False
    assert report.results[0].status == "error"


def test_issue_title_and_body_formatting():
    result = DriftCheckResult(
        slug="bestbuy_ca",
        url="https://www.bestbuy.ca/example",
        scenario="in_stock",
        status="shape_mismatch",
        message="Live scrape fingerprint differs from committed baseline",
        diff={"extraction": {"baseline": "jsonld", "live": "opengraph"}},
    )
    assert issue_title("bestbuy_ca", "shape_mismatch") == (
        "[retailer-drift] bestbuy_ca — shape mismatch"
    )
    body = format_issue_body(result, run_url="https://example.test/run/1")
    assert "bestbuy_ca" in body
    assert "Fingerprint diff" in body
    assert "https://example.test/run/1" in body


def test_resolve_github_repo_from_env(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/shopping-monitor")
    repo = resolve_github_repo()
    assert repo.slug == "acme/shopping-monitor"


def test_github_issue_client_dry_run_create_and_close():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"items": []}))
    client = httpx.Client(transport=transport)
    gh = GitHubIssueClient(
        token="test-token",
        repo=GitHubRepo(owner="acme", name="shopping-monitor"),
        dry_run=True,
        http_client=client,
    )
    failing = DriftCheckResult(
        slug="palmisleskate",
        url="https://example.test",
        scenario="in_stock",
        status="blocked",
        message="blocked",
    )
    assert "dry-run would create issue" in gh.sync_result(failing)
    passing = DriftCheckResult(
        slug="palmisleskate",
        url="https://example.test",
        scenario="in_stock",
        status="ok",
    )
    assert "dry-run would close" in gh.sync_result(passing)
    gh.close()


def test_write_baseline_roundtrip(tmp_path, monkeypatch):
    slug = "palmisleskate"
    fingerprint = normalize(scrape_fixture_baseline(slug, "in_stock"))
    target = tmp_path / f"{slug}.json"
    monkeypatch.setattr(
        "scrapers.drift.compare.snapshot_path",
        lambda requested_slug: target if requested_slug == slug else snapshot_path(requested_slug),
    )
    write_baseline(slug, fingerprint)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert DriftSnapshot.model_validate(loaded) == fingerprint


def test_check_retailer_drift_script_rejects_fixtures_mode(monkeypatch):
    monkeypatch.setenv("SCRAPER_MODE", "fixtures")
    result = subprocess.run(
        [sys.executable, "scripts/check_retailer_drift.py", "--no-issues"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Expected SCRAPER_MODE" in result.stderr or "SCRAPER_MODE must be live" in result.stderr


def test_update_drift_snapshots_script_writes_baselines(monkeypatch):
    monkeypatch.setenv("SCRAPER_MODE", "fixtures")
    result = subprocess.run(
        [sys.executable, "scripts/update_drift_snapshots.py", "--slug", "palmisleskate"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Wrote drift baseline: palmisleskate" in result.stdout


def test_update_drift_snapshots_script_requires_fixtures_mode(monkeypatch):
    monkeypatch.setenv("SCRAPER_MODE", "live")
    result = subprocess.run(
        [sys.executable, "scripts/update_drift_snapshots.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
