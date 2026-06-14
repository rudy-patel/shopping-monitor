"""Per-strategy benchmark runners."""

from __future__ import annotations

import time

from scrapers.benchmark.fields import detect_blocked_markers, evaluate_fields, skipped_fields
from scrapers.benchmark.parsers import get_parser
from scrapers.benchmark.playwright_fetch import fetch_html_with_playwright
from scrapers.benchmark.retailer_probes import RETAILER_API_NAMES, RETAILER_API_PROBES
from scrapers.benchmark.types import (
    CatalogEntry,
    HttpParseAttempt,
    StrategyFields,
    StrategyId,
    StrategyResult,
    StrategyStatus,
)
from scrapers.exceptions import (
    NetworkBlockedInFixturesError,  # pragma: allowlist secret
    ScrapeBlockedError,
)
from scrapers.extraction.types import ExtractedFields
from scrapers.fixture_url import resolve_fixture_scenario
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret
from scrapers.http import scraper_fetch
from scrapers.mode import is_fixtures_mode  # pragma: allowlist secret


def run_structured_data(
    entry: CatalogEntry,
    *,
    live: bool,
    retries: int,
) -> StrategyResult:
    if live and is_fixtures_mode():  # pragma: allowlist secret
        return _skipped("structured_data", reason="fixture_mode_requires_live")

    start = time.perf_counter()
    retry_count = 0
    last_error: str | None = None

    for attempt in range(retries + 1):
        if attempt > 0:
            retry_count += 1
        try:
            html = _load_html(entry, live=live)
            parser = get_parser(entry.slug)
            extracted = parser(html, entry.url)
            fields = evaluate_fields(extracted, expect=entry.expect)
            status = _status_from_fields(fields, entry.expect)
            return StrategyResult(
                strategy="structured_data",
                status=status,
                fields=fields,
                runtime_ms=_elapsed_ms(start),
                retry_count=retry_count,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)

    return StrategyResult(
        strategy="structured_data",
        status="failed",
        fields=evaluate_fields(None, expect=entry.expect, error=last_error),
        runtime_ms=_elapsed_ms(start),
        retry_count=retry_count,
        reason=last_error,
    )


def run_http_parse(
    entry: CatalogEntry,
    *,
    live: bool,
    retries: int,
) -> StrategyResult:
    if is_fixtures_mode() and not live:  # pragma: allowlist secret
        return _skipped("http_parse", reason="skipped_in_fixture_mode")

    if not live:
        return _skipped("http_parse", reason="live_mode_required")

    start = time.perf_counter()
    retry_count = 0
    attempts: list[HttpParseAttempt] = []
    last_error: str | None = None
    parser = get_parser(entry.slug)

    for attempt in range(retries + 1):
        if attempt > 0:
            retry_count += 1
        try:
            response = scraper_fetch(entry.url, retailer_slug=entry.slug)
            markers = detect_blocked_markers(response.status_code, response.body_text)
            if markers:
                attempts.append(
                    HttpParseAttempt(
                        kind="html",
                        status="blocked",
                        blocked_markers=markers,
                    )
                )
                extracted = _try_retailer_api_probe(entry, attempts)
                if extracted is not None:
                    fields = evaluate_fields(extracted, expect=entry.expect)
                    return StrategyResult(
                        strategy="http_parse",
                        status=_status_from_fields(fields, entry.expect),
                        fields=fields,
                        runtime_ms=_elapsed_ms(start),
                        retry_count=retry_count,
                        blocked=True,
                        blocked_markers=markers,
                        http_status=response.status_code,
                        http_parse_attempts=attempts,
                    )
                last_error = "html_blocked"
                continue

            extracted = parser(response.body_text, entry.url)
            if extracted.price_cents is None:
                attempts.append(
                    HttpParseAttempt(kind="html", status="failed", reason="missing_price")
                )
                api_extracted = _try_retailer_api_probe(entry, attempts)
                if api_extracted is not None:
                    fields = evaluate_fields(api_extracted, expect=entry.expect)
                    return StrategyResult(
                        strategy="http_parse",
                        status=_status_from_fields(fields, entry.expect),
                        fields=fields,
                        runtime_ms=_elapsed_ms(start),
                        retry_count=retry_count,
                        http_status=response.status_code,
                        http_parse_attempts=attempts,
                    )
                last_error = "missing_price"
                continue

            attempts.append(HttpParseAttempt(kind="html", status="success"))
            fields = evaluate_fields(extracted, expect=entry.expect)
            return StrategyResult(
                strategy="http_parse",
                status=_status_from_fields(fields, entry.expect),
                fields=fields,
                runtime_ms=_elapsed_ms(start),
                retry_count=retry_count,
                http_status=response.status_code,
                http_parse_attempts=attempts,
            )
        except ScrapeBlockedError:
            markers = ["blocked"]
            attempts.append(
                HttpParseAttempt(kind="html", status="blocked", blocked_markers=markers)
            )
            extracted = _try_retailer_api_probe(entry, attempts)
            if extracted is not None:
                fields = evaluate_fields(extracted, expect=entry.expect)
                return StrategyResult(
                    strategy="http_parse",
                    status=_status_from_fields(fields, entry.expect),
                    fields=fields,
                    runtime_ms=_elapsed_ms(start),
                    retry_count=retry_count,
                    blocked=True,
                    blocked_markers=markers,
                    http_parse_attempts=attempts,
                )
            last_error = "scrape_blocked"
        except NetworkBlockedInFixturesError:  # pragma: allowlist secret
            return _skipped("http_parse", reason="skipped_in_fixture_mode")
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)

    return StrategyResult(
        strategy="http_parse",
        status="failed",
        fields=evaluate_fields(None, expect=entry.expect, error=last_error),
        runtime_ms=_elapsed_ms(start),
        retry_count=retry_count,
        reason=last_error,
        http_parse_attempts=attempts,
    )


def run_playwright(
    entry: CatalogEntry,
    *,
    live: bool,
    with_playwright: bool,
    retries: int,
) -> StrategyResult:
    if not with_playwright:
        return _skipped("playwright", reason="playwright_not_requested")

    try:
        from scrapers.benchmark.playwright_fetch import playwright_available
    except ImportError:
        return _skipped("playwright", reason="playwright_not_installed")

    if not playwright_available():
        return _skipped("playwright", reason="playwright_not_installed")

    if not live:
        return _skipped("playwright", reason="live_mode_required")

    if is_fixtures_mode():  # pragma: allowlist secret
        return _skipped("playwright", reason="skipped_in_fixture_mode")

    start = time.perf_counter()
    retry_count = 0
    last_error: str | None = None
    parser = get_parser(entry.slug)

    for attempt in range(retries + 1):
        if attempt > 0:
            retry_count += 1
        try:
            html = fetch_html_with_playwright(entry.url)
            extracted = parser(html, entry.url)
            fields = evaluate_fields(extracted, expect=entry.expect)
            return StrategyResult(
                strategy="playwright",
                status=_status_from_fields(fields, entry.expect),
                fields=fields,
                runtime_ms=_elapsed_ms(start),
                retry_count=retry_count,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)

    return StrategyResult(
        strategy="playwright",
        status="failed",
        fields=evaluate_fields(None, expect=entry.expect, error=last_error),
        runtime_ms=_elapsed_ms(start),
        retry_count=retry_count,
        reason=last_error,
    )


def _try_retailer_api_probe(
    entry: CatalogEntry,
    attempts: list[HttpParseAttempt],
) -> ExtractedFields | None:
    probe = RETAILER_API_PROBES.get(entry.slug)
    if probe is None:
        return None
    try:
        extracted = probe(entry.url)
        attempts.append(
            HttpParseAttempt(
                kind="retailer_api",
                status="success",
                api=RETAILER_API_NAMES.get(entry.slug),
            )
        )
        return extracted
    except Exception as exc:  # noqa: BLE001
        attempts.append(
            HttpParseAttempt(
                kind="retailer_api",
                status="failed",
                api=RETAILER_API_NAMES.get(entry.slug),
                reason=str(exc),
            )
        )
        return None


def _load_html(entry: CatalogEntry, *, live: bool) -> str:
    if live and not is_fixtures_mode():  # pragma: allowlist secret
        response = scraper_fetch(entry.url, retailer_slug=entry.slug)
        return response.body_text

    scenario = resolve_fixture_scenario(entry.url, entry.slug)
    return FixtureLoader().load_text(entry.slug, scenario)


def _status_from_fields(fields: StrategyFields, expect) -> StrategyStatus:
    checks = (
        (expect.title, fields.title.ok),
        (expect.price, fields.price.ok),
        (expect.stock, fields.stock.ok),
        (expect.image, fields.image.ok),
        (expect.variants, fields.variants.ok),
    )
    if all(not required or ok for required, ok in checks):
        return "success"
    return "failed"


def _skipped(strategy: StrategyId, *, reason: str) -> StrategyResult:
    return StrategyResult(
        strategy=strategy,
        status="skipped",
        fields=skipped_fields(reason),
        reason=reason,
    )


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)
