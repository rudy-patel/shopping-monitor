"""Unit tests for SearchCacheService (T8.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.settings import Settings
from services.search_cache_service import (
    SearchCacheService,
    cache_reads_enabled,
    cache_writes_enabled,
    hash_query,
    is_untrusted_cache_payload,
    normalize_query,
)
from test.fake_supabase import FakeSupabaseClient

_LIVE_SETTINGS = Settings(scraper_mode="live")


def test_normalize_query_collapses_whitespace_and_case():
    assert normalize_query("  Hello   WORLD\t") == "hello world"


def test_hash_query_stable():
    assert hash_query("hello world") == hash_query("hello world")
    assert hash_query("hello world") != hash_query("hello worlds")


def test_get_returns_none_when_missing():
    client = FakeSupabaseClient()
    service = SearchCacheService(client, settings=_LIVE_SETTINGS)
    assert service.get("nothing here") is None


def test_put_then_get_returns_payload():
    client = FakeSupabaseClient()
    service = SearchCacheService(client, settings=_LIVE_SETTINGS)
    payload = {"results": [{"title": "x"}]}
    service.put("Hello World", payload)
    hit = service.get("hello   world")  # normalization makes this a hit
    assert hit is not None
    assert hit.payload == payload


def test_get_returns_none_when_expired():
    client = FakeSupabaseClient()
    service = SearchCacheService(
        client,
        settings=Settings(scraper_mode="live", search_cache_ttl_hours=1),
    )
    payload = {"results": []}
    service.put("query", payload)
    # Walk fetched_at back 2h to simulate expiry.
    row = next(iter(client.search_cache.values()))
    row["fetched_at"] = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    assert service.get("query") is None


def test_get_empty_query_returns_none():
    client = FakeSupabaseClient()
    service = SearchCacheService(client, settings=_LIVE_SETTINGS)
    assert service.get("   ") is None


def test_put_overwrites_existing_entry():
    client = FakeSupabaseClient()
    service = SearchCacheService(client, settings=_LIVE_SETTINGS)
    service.put("query", {"results": [{"title": "old"}]})
    service.put("query", {"results": [{"title": "new"}]})
    assert len(client.search_cache) == 1
    hit = service.get("query")
    assert hit is not None
    assert hit.payload == {"results": [{"title": "new"}]}


def test_is_untrusted_cache_payload_detects_fixture_urls():
    payload = {
        "results": [
            {
                "url": "https://fixtures.local/bestbuy_ca/in_stock",
                "title": "Widget",
            }
        ]
    }
    assert is_untrusted_cache_payload(payload) is True
    assert is_untrusted_cache_payload({"results": [{"url": "https://www.bestbuy.ca/p/1", "title": "x"}]}) is False


def test_get_ignores_poisoned_cache_row():
    client = FakeSupabaseClient()
    service = SearchCacheService(client, settings=_LIVE_SETTINGS)
    query_hash = hash_query(normalize_query("airpods pro"))
    client.search_cache[query_hash] = {
        "query_hash": query_hash,
        "query": "airpods pro",
        "result_payload": {
            "results": [
                {
                    "url": "https://fixtures.local/apple_ca/in_stock",
                    "title": "AirPods",
                }
            ]
        },
        "fetched_at": datetime.now(UTC).isoformat(),
    }
    assert service.get("airpods pro") is None


def test_put_skips_poisoned_payload():
    client = FakeSupabaseClient()
    service = SearchCacheService(client, settings=_LIVE_SETTINGS)
    service.put(
        "query",
        {"results": [{"url": "https://fixtures.local/generic/in_stock", "title": "x"}]},
    )
    assert client.search_cache == {}


def test_cache_disabled_in_fixtures_mode():
    client = FakeSupabaseClient()
    service = SearchCacheService(client, settings=Settings(scraper_mode="fixtures"))
    assert cache_reads_enabled(service._settings) is False
    assert cache_writes_enabled(service._settings) is False
    service.put("query", {"results": [{"url": "https://www.bestbuy.ca/p/1", "title": "x"}]})
    assert client.search_cache == {}
    assert service.get("query") is None
