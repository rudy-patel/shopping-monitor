"""Unit tests for search orchestrator (T8.2)."""

from __future__ import annotations

import pytest

from scrapers.bestbuy_ca import register_bestbuy_ca
from scrapers.generic import register_generic
from scrapers.indigo import register_indigo
from scrapers.registry import reset_registry
from services.llm import FakeLlmProvider, LlmSearchCandidate, LlmSearchResult
from services.search_cache_service import SearchCacheService
from services.search_service import (
    MAX_SEARCH_RESULTS,
    _classify_candidate,
    _dedupe_and_rank,
    _is_canadian_host,
    run_search,
)
from test.fake_supabase import FakeSupabaseClient


@pytest.fixture(autouse=True)
def _registry():
    reset_registry()
    register_generic()
    register_bestbuy_ca()
    register_indigo()
    yield
    reset_registry()


def _candidate(
    url: str,
    *,
    title: str = "Sample",
    retailer_hint: str | None = None,
    brand: str | None = None,
    justification: str = "match",
) -> LlmSearchCandidate:
    return LlmSearchCandidate(
        url=url,
        title=title,
        retailer_hint=retailer_hint,
        brand_hint=brand,
        justification=justification,
    )


def test_classify_supported_retailer_returns_slug_and_label():
    candidate = _candidate(
        "https://www.bestbuy.ca/en-ca/product/widget/12345",
        title="Best Buy Widget",
        retailer_hint="Best Buy Canada",
    )
    item = _classify_candidate(candidate)
    assert item is not None
    assert item.supported is True
    assert item.retailer_slug == "bestbuy_ca"
    assert item.retailer_label == "Best Buy Canada"


def test_classify_unsupported_retailer_falls_back_to_generic():
    candidate = _candidate(
        "https://walmart.ca/en/ip/widget/123",
        title="Walmart Widget",
        retailer_hint="Walmart Canada",
    )
    item = _classify_candidate(candidate)
    assert item is not None
    assert item.supported is False
    assert item.retailer_slug == "generic"
    assert item.retailer_label == "Walmart Canada"  # uses the hint


def test_classify_unsupported_no_hint_derives_from_host():
    candidate = _candidate(
        "https://londondrugs.com/widget.html",
        title="LD Widget",
    )
    item = _classify_candidate(candidate)
    assert item is not None
    assert item.retailer_label == "Londondrugs"


def test_is_canadian_host_allows_ca_and_generic_com():
    assert _is_canadian_host("https://www.bestbuy.ca/en-ca/p")
    assert _is_canadian_host("https://walmart.ca/en/ip/x")
    assert _is_canadian_host("https://apple.com/ca/something")


def test_is_canadian_host_blocks_country_tlds():
    assert not _is_canadian_host("https://retailer.us/p")
    assert not _is_canadian_host("https://retailer.uk/p")
    assert not _is_canadian_host("https://retailer.de/p")
    assert not _is_canadian_host("https://retailer.jp/p")


def test_is_canadian_host_rejects_blank_host():
    assert not _is_canadian_host("not-a-url")


def test_dedupe_supported_retailer_only_kept_once():
    items = [
        _classify_candidate(_candidate("https://www.bestbuy.ca/p/a", title="A")),
        _classify_candidate(_candidate("https://www.bestbuy.ca/p/b", title="B")),
        _classify_candidate(_candidate("https://www.indigo.ca/p/c", title="C")),
    ]
    result = _dedupe_and_rank(items)
    slugs = [item.retailer_slug for item in result]
    assert slugs == ["bestbuy_ca", "indigo"]


def test_dedupe_ranks_supported_before_unsupported():
    items = [
        _classify_candidate(_candidate("https://walmart.ca/x", title="Walmart Item")),
        _classify_candidate(_candidate("https://www.bestbuy.ca/p/y", title="Best Buy Item")),
    ]
    result = _dedupe_and_rank(items)
    assert result[0].retailer_slug == "bestbuy_ca"
    assert result[1].retailer_slug == "generic"


def test_dedupe_caps_results():
    items = [
        _classify_candidate(_candidate(f"https://store{i}.ca/p", title=f"Item {i}"))
        for i in range(8)
    ]
    result = _dedupe_and_rank(items)
    assert len(result) == MAX_SEARCH_RESULTS


def test_run_search_calls_llm_then_caches():
    llm = FakeLlmProvider(
        search_result=LlmSearchResult(
            candidates=[
                _candidate(
                    "https://www.bestbuy.ca/en-ca/product/widget/1",
                    title="Best Buy Widget",
                ),
                _candidate(
                    "https://walmart.ca/en/ip/widget/2",
                    title="Walmart Widget",
                ),
            ]
        )
    )
    client = FakeSupabaseClient()
    cache = SearchCacheService(client)

    first = run_search("widget", client=client, llm=llm, cache=cache)
    assert first.cache_hit is False
    assert len(first.results) == 2
    assert first.results[0].supported is True
    assert first.results[1].supported is False
    assert len(llm.search_calls) == 1

    # Second call should hit the cache.
    second = run_search("widget", client=client, llm=llm, cache=cache)
    assert second.cache_hit is True
    assert len(second.results) == 2
    assert len(llm.search_calls) == 1  # not re-called


def test_run_search_empty_query_filters_out_non_canadian():
    llm = FakeLlmProvider(
        search_result=LlmSearchResult(
            candidates=[
                _candidate("https://shop.us/widget", title="US Widget"),
            ]
        )
    )
    client = FakeSupabaseClient()
    cache = SearchCacheService(client)

    response = run_search("widget", client=client, llm=llm, cache=cache)
    assert response.results == []
