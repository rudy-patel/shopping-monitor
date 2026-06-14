"""Benchmark harness orchestration."""

from __future__ import annotations

from datetime import datetime, timezone

from scrapers.benchmark.catalog import load_catalog
from scrapers.benchmark.playwright_fetch import playwright_available
from scrapers.benchmark.recommend import build_summaries
from scrapers.benchmark.strategies import run_http_parse, run_playwright, run_structured_data
from scrapers.benchmark.types import BenchmarkReport, BenchmarkRun
from scrapers.mode import get_scraper_mode


def run_benchmark(
    *,
    slugs: list[str] | None = None,
    live: bool = False,
    with_playwright: bool = False,
    retries: int | None = None,
) -> BenchmarkReport:
    catalog_version, entries = load_catalog(slugs=slugs)
    if not entries:
        raise ValueError("No catalog entries matched the filter.")

    effective_retries = retries if retries is not None else (1 if live else 0)
    runs: list[BenchmarkRun] = []

    for entry in entries:
        strategies = [
            run_structured_data(entry, live=live, retries=effective_retries),
            run_http_parse(entry, live=live, retries=effective_retries),
            run_playwright(
                entry,
                live=live,
                with_playwright=with_playwright,
                retries=effective_retries,
            ),
        ]
        runs.append(
            BenchmarkRun(
                slug=entry.slug,
                scenario=entry.scenario,
                url=entry.url,
                expect=entry.expect,
                strategies=strategies,
            )
        )

    return BenchmarkReport(
        generated_at=datetime.now(timezone.utc),
        scraper_mode=get_scraper_mode().value,
        playwright_available=playwright_available(),
        catalog_version=catalog_version,
        runs=runs,
        summaries=build_summaries(runs),
    )
