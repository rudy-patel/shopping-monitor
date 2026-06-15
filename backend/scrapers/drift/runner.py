"""Run drift checks against live URLs or injected mock scrapers."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timezone

from scrapers.contract import ProductSnapshot
from scrapers.drift.catalog import load_catalog
from scrapers.drift.compare import compare_to_baseline
from scrapers.drift.github_issues import GitHubIssueClient, resolve_github_repo
from scrapers.drift.types import DriftCatalogEntry, DriftCheckResult, DriftReport
from scrapers.exceptions import (
    NotCanadianListingError,
    ScrapeBlockedError,
    ScrapeParseError,
    ScrapeTimeoutError,
    ScraperError,
)
from scrapers.mode import get_scraper_mode
from scrapers.registry import get

LiveScrapeFn = Callable[[str, str], ProductSnapshot]

_RETRY_SLEEP_S = 1.0


def run_drift_checks(
    *,
    slugs: list[str] | None = None,
    live_scrape_fn: LiveScrapeFn | None = None,
    file_issues: bool = False,
    dry_run: bool = False,
    run_url: str | None = None,
    github_token: str | None = None,
) -> DriftReport:
    catalog_version, entries = load_catalog(slugs=slugs)
    if not entries:
        raise ValueError("No drift catalog entries matched the requested slugs")

    results = [
        _check_entry(entry, live_scrape_fn=live_scrape_fn)
        for entry in entries
    ]

    report = DriftReport(
        generated_at=datetime.now(timezone.utc),
        scraper_mode=get_scraper_mode().value,
        catalog_version=catalog_version,
        dry_run=dry_run,
        file_issues=file_issues,
        results=results,
    )

    if file_issues and github_token:
        repo = resolve_github_repo()
        with GitHubIssueClient(token=github_token, repo=repo, dry_run=dry_run) as client:
            client.ensure_label()
            for result in results:
                client.sync_result(result, run_url=run_url)

    return report


def _check_entry(
    entry: DriftCatalogEntry,
    *,
    live_scrape_fn: LiveScrapeFn | None,
) -> DriftCheckResult:
    slug = entry.slug
    url = entry.url
    scenario = entry.scenario
    expect = entry.expect

    try:
        snapshot = _scrape_with_retry(slug, url, live_scrape_fn=live_scrape_fn)
    except ScrapeBlockedError as exc:
        return DriftCheckResult(
            slug=slug,
            url=url,
            scenario=scenario,
            status="blocked",
            message=str(exc),
            blocked_markers=_blocked_markers_from_error(exc),
        )
    except (ScrapeParseError, ScrapeTimeoutError, NotCanadianListingError) as exc:
        return DriftCheckResult(
            slug=slug,
            url=url,
            scenario=scenario,
            status="error",
            message=str(exc),
        )
    except ScraperError as exc:
        return DriftCheckResult(
            slug=slug,
            url=url,
            scenario=scenario,
            status="error",
            message=str(exc),
        )

    ok, diff, baseline, live_fingerprint, expect_failures = compare_to_baseline(
        slug=slug,
        live_snapshot=snapshot,
        expect=expect,
    )
    if ok:
        return DriftCheckResult(
            slug=slug,
            url=url,
            scenario=scenario,
            status="ok",
            baseline_fingerprint=baseline,
            live_fingerprint=live_fingerprint,
        )

    status = "shape_mismatch" if diff else "error"
    message = None
    if diff:
        message = "Live scrape fingerprint differs from committed baseline"
    elif expect_failures:
        message = f"Missing expected fields: {', '.join(expect_failures)}"

    return DriftCheckResult(
        slug=slug,
        url=url,
        scenario=scenario,
        status=status,
        message=message,
        diff=diff or None,
        expect_failures=expect_failures,
        baseline_fingerprint=baseline,
        live_fingerprint=live_fingerprint,
    )


def _scrape_with_retry(
    slug: str,
    url: str,
    *,
    live_scrape_fn: LiveScrapeFn | None,
) -> ProductSnapshot:
    last_error: ScraperError | None = None
    for attempt in range(2):
        try:
            return _scrape_live(slug, url, live_scrape_fn=live_scrape_fn)
        except ScrapeBlockedError as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(_RETRY_SLEEP_S)
                continue
            raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("unreachable")


def _scrape_live(
    slug: str,
    url: str,
    *,
    live_scrape_fn: LiveScrapeFn | None,
) -> ProductSnapshot:
    if live_scrape_fn is not None:
        return live_scrape_fn(slug, url)
    return get(slug).scrape(url)


def scrape_fixture_baseline(slug: str, scenario: str) -> ProductSnapshot:
    """Fixture-mode scrape used to regenerate committed baselines."""
    fixture_url = f"https://fixtures.local/{slug}/{scenario}"
    return get(slug).scrape(fixture_url)


def _blocked_markers_from_error(exc: ScrapeBlockedError) -> list[str]:
    markers = ["scrape_blocked"]
    message = str(exc).lower()
    for marker in ("cloudflare", "captcha", "access denied", "403", "429"):
        if marker in message:
            markers.append(marker.replace(" ", "_"))
    return markers
