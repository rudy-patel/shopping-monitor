"""Search orchestrator: query → classified, deduped, capped results (T8.2)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from core.logging import get_logger
from scrapers.registry import lookup_by_url
from services.factory import get_llm_provider
from services.llm import LlmProvider, LlmSearchCandidate, LlmSearchResult
from services.retailer_labels import label_for_slug, label_from_url
from services.search_cache_service import SearchCacheService

logger = get_logger(__name__)

MAX_SEARCH_RESULTS = 5


@dataclass(frozen=True)
class SearchResultItem:
    title: str
    retailer_slug: str
    retailer_label: str
    url: str
    supported: bool
    brand_hint: str | None
    justification: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "retailer_slug": self.retailer_slug,
            "retailer_label": self.retailer_label,
            "url": self.url,
            "supported": self.supported,
            "brand_hint": self.brand_hint,
            "justification": self.justification,
        }


@dataclass(frozen=True)
class SearchResponse:
    query: str
    results: list[SearchResultItem]
    cache_hit: bool
    latency_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "results": [item.to_dict() for item in self.results],
            "cache_hit": self.cache_hit,
            "latency_ms": self.latency_ms,
        }


def _normalize_url(url: str) -> str:
    return url.strip().lower().rstrip("/")


def _classify_candidate(candidate: LlmSearchCandidate) -> SearchResultItem:
    """Classify one Gemini candidate as supported (registered retailer) or generic.

    `lookup_by_url` always resolves to a registered entry because the `generic`
    scraper is the fallback, so this never returns None.
    """
    url = str(candidate.url)
    entry = lookup_by_url(url)
    if entry.slug == "generic":
        return _build_generic_item(candidate)

    return SearchResultItem(
        title=candidate.title.strip() or "Untitled product",
        retailer_slug=entry.slug,
        retailer_label=label_for_slug(entry.slug),
        url=url,
        supported=True,
        brand_hint=candidate.brand_hint,
        justification=candidate.justification.strip(),
    )


def _build_generic_item(candidate: LlmSearchCandidate) -> SearchResultItem:
    url = str(candidate.url)
    return SearchResultItem(
        title=candidate.title.strip() or "Untitled product",
        retailer_slug="generic",
        retailer_label=label_from_url(url, fallback=candidate.retailer_hint),
        url=url,
        supported=False,
        brand_hint=candidate.brand_hint,
        justification=candidate.justification.strip(),
    )


_BLOCKED_TLDS = (".us", ".uk", ".au", ".eu", ".de", ".fr", ".jp")


def _is_canadian_host(url: str) -> bool:
    """Allow .ca hosts and generic .com (the scrape step rejects non-CAD pages)."""
    host = (urlsplit(url).hostname or "").lower()
    if not host:
        return False
    if host.endswith(".ca"):
        return True
    return not any(host.endswith(suffix) for suffix in _BLOCKED_TLDS)


def _dedupe_and_rank(
    items: list[SearchResultItem],
    *,
    cap: int = MAX_SEARCH_RESULTS,
) -> list[SearchResultItem]:
    seen_supported: set[str] = set()
    seen_urls: set[str] = set()
    supported: list[SearchResultItem] = []
    unsupported: list[SearchResultItem] = []

    for item in items:
        url_key = _normalize_url(item.url)
        if url_key in seen_urls:
            continue
        seen_urls.add(url_key)

        if item.supported:
            if item.retailer_slug in seen_supported:
                continue
            seen_supported.add(item.retailer_slug)
            supported.append(item)
        else:
            unsupported.append(item)

    combined = supported + unsupported
    return combined[:cap]


def run_search(
    query: str,
    *,
    client: Any,
    llm: LlmProvider | None = None,
    cache: SearchCacheService | None = None,
) -> SearchResponse:
    """End-to-end: cache → LLM → classify → dedupe → cap → cache write."""
    started = time.perf_counter()
    cache = cache or SearchCacheService(client)
    normalized_query = query.strip()

    cache_hit = cache.get(query)
    if cache_hit is not None:
        items_raw = cache_hit.payload.get("results") or []
        items = [SearchResultItem(**item) for item in items_raw]
        logger.info(
            "search_cache_hit",
            extra={"query_length": len(query), "result_count": len(items)},
        )
        return SearchResponse(
            query=normalized_query,
            results=items,
            cache_hit=True,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    llm = llm or get_llm_provider()
    logger.info("search_gemini_called", extra={"query_length": len(query)})
    result: LlmSearchResult = llm.search(query=normalized_query)

    classified: list[SearchResultItem] = []
    for candidate in result.candidates:
        if not _is_canadian_host(str(candidate.url)):
            continue
        classified.append(_classify_candidate(candidate))

    ranked = _dedupe_and_rank(classified)

    logger.info(
        "search_completed",
        extra={
            "query_length": len(query),
            "result_count": len(ranked),
            "supported_count": sum(1 for r in ranked if r.supported),
            "cache_hit": False,
        },
    )

    cache.put(query, {"results": [item.to_dict() for item in ranked]})

    return SearchResponse(
        query=normalized_query,
        results=ranked,
        cache_hit=False,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
