"""Recommend default and fallback strategies per retailer slug."""

from __future__ import annotations

from collections import defaultdict

from scrapers.benchmark.fields import has_title_or_price, score_strategy_fields
from scrapers.benchmark.types import (
    BenchmarkRun,
    FieldExpect,
    SlugSummary,
    StrategyId,
    StrategyResult,
)
from scrapers.benchmark.retailer_probes import RETAILER_API_PROBES
from scrapers.contract import ScrapeSource

_STRATEGY_ORDER: tuple[StrategyId, ...] = (
    "structured_data",
    "http_parse",
    "playwright",
)

_SOURCE_BY_STRATEGY: dict[StrategyId, ScrapeSource] = {
    "structured_data": ScrapeSource.STRUCTURED_DATA,
    "http_parse": ScrapeSource.HTTP_PARSE,
    "playwright": ScrapeSource.PLAYWRIGHT,
}

_DEFAULT_NOTES: dict[str, str] = {
    "generic": "JSON-LD/OG sufficient on fixtures.",
    "palmisleskate": "Shopify JSON-LD + theme meta; structured_data covers title/price/stock/variants on fixtures.",
    "tikiroomskate": "Shopify JSON-LD + theme meta; structured_data covers title/price/stock/variants on fixtures.",
    "indigo": "Shopify meta plus ProductGroup JSON-LD for format-level stock on fixtures.",
    "apple_ca": "Apple buy-flow JSON-LD plus config grid HTML for variants on fixtures.",
    "abercrombie": "JSON-LD title/stock plus embedded productPrices and scoped SKU inventory on fixtures.",
    "bestbuy_ca": (
        "Fixture HTML succeeds via structured_data; live HTML likely blocked — "
        "http_parse retailer_api sub-probe expected in production."
    ),
}


def build_summaries(runs: list[BenchmarkRun]) -> list[SlugSummary]:
    by_slug: dict[str, list[BenchmarkRun]] = defaultdict(list)
    for run in runs:
        by_slug[run.slug].append(run)

    summaries: list[SlugSummary] = []
    for slug in sorted(by_slug):
        slug_runs = by_slug[slug]
        aggregated = _aggregate_strategy_results(slug_runs)
        default_strategy = _pick_default(aggregated, slug_runs)
        fallbacks = _pick_fallbacks(aggregated, default_strategy)
        fallbacks = _apply_advisory_fallbacks(slug, default_strategy, fallbacks)
        summaries.append(
            SlugSummary(
                slug=slug,
                default_strategy=default_strategy,
                fallback_strategies=fallbacks,
                registry_snippet=_registry_snippet(default_strategy, fallbacks),
                notes=_DEFAULT_NOTES.get(slug),
            )
        )
    return summaries


def _aggregate_strategy_results(
    runs: list[BenchmarkRun],
) -> dict[StrategyId, list[StrategyResult]]:
    aggregated: dict[StrategyId, list[StrategyResult]] = defaultdict(list)
    for run in runs:
        for result in run.strategies:
            if result.status != "skipped":
                aggregated[result.strategy].append(result)
    return aggregated


def _pick_default(
    aggregated: dict[StrategyId, list[StrategyResult]],
    runs: list[BenchmarkRun],
) -> StrategyId:
    best: tuple[int, float, int, StrategyId] | None = None
    expect = _merged_expect(runs)

    for order_idx, strategy in enumerate(_STRATEGY_ORDER):
        results = aggregated.get(strategy, [])
        if not results:
            continue
        score = sum(score_strategy_fields(r.fields, expect) for r in results)
        if score == 0:
            continue
        avg_runtime = sum(r.runtime_ms for r in results) / len(results)
        candidate = (score, -avg_runtime, -order_idx, strategy)
        if best is None or candidate > best:
            best = candidate

    return best[3] if best is not None else "structured_data"


def _pick_fallbacks(
    aggregated: dict[StrategyId, list[StrategyResult]],
    default_strategy: StrategyId,
) -> list[StrategyId]:
    fallbacks: list[StrategyId] = []
    for strategy in _STRATEGY_ORDER:
        if strategy == default_strategy:
            continue
        results = aggregated.get(strategy, [])
        if not results:
            continue
        if any(has_title_or_price(r.fields) for r in results):
            fallbacks.append(strategy)
    return fallbacks


def _apply_advisory_fallbacks(
    slug: str,
    default_strategy: StrategyId,
    fallbacks: list[StrategyId],
) -> list[StrategyId]:
    """Include wired retailer API probes as http_parse fallbacks when untested in fixtures."""
    if (
        slug in RETAILER_API_PROBES
        and default_strategy == "structured_data"
        and "http_parse" not in fallbacks
    ):
        return [*fallbacks, "http_parse"]
    return fallbacks


def _merged_expect(runs: list[BenchmarkRun]) -> FieldExpect:
    merged = FieldExpect(
        title=False,
        price=False,
        stock=False,
        image=False,
        variants=False,
    )
    for run in runs:
        if run.expect.title:
            merged.title = True
        if run.expect.price:
            merged.price = True
        if run.expect.stock:
            merged.stock = True
        if run.expect.image:
            merged.image = True
        if run.expect.variants:
            merged.variants = True
    return merged


def _registry_snippet(
    default_strategy: StrategyId,
    fallbacks: list[StrategyId],
) -> str:
    default = _SOURCE_BY_STRATEGY[default_strategy]
    if fallbacks:
        fallback_sources = ", ".join(
            f"ScrapeSource.{_SOURCE_BY_STRATEGY[s].name}"
            for s in fallbacks
        )
        return (
            f"default_strategy=ScrapeSource.{default.name}, "
            f"fallback_strategies=({fallback_sources},)"
        )
    return f"default_strategy=ScrapeSource.{default.name}, fallback_strategies=()"
