"""Unit tests for SearchCacheService (T8.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.settings import Settings
from services.search_cache_service import (
    SearchCacheService,
    hash_query,
    normalize_query,
)
from test.fake_supabase import FakeSupabaseClient


def test_normalize_query_collapses_whitespace_and_case():
    assert normalize_query("  Hello   WORLD\t") == "hello world"


def test_hash_query_stable():
    assert hash_query("hello world") == hash_query("hello world")
    assert hash_query("hello world") != hash_query("hello worlds")


def test_get_returns_none_when_missing():
    client = FakeSupabaseClient()
    service = SearchCacheService(client)
    assert service.get("nothing here") is None


def test_put_then_get_returns_payload():
    client = FakeSupabaseClient()
    service = SearchCacheService(client)
    payload = {"results": [{"title": "x"}]}
    service.put("Hello World", payload)
    hit = service.get("hello   world")  # normalization makes this a hit
    assert hit is not None
    assert hit.payload == payload


def test_get_returns_none_when_expired():
    client = FakeSupabaseClient()
    service = SearchCacheService(client, settings=Settings(search_cache_ttl_hours=1))
    payload = {"results": []}
    service.put("query", payload)
    # Walk fetched_at back 2h to simulate expiry.
    row = next(iter(client.search_cache.values()))
    row["fetched_at"] = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    assert service.get("query") is None


def test_get_empty_query_returns_none():
    client = FakeSupabaseClient()
    service = SearchCacheService(client)
    assert service.get("   ") is None


def test_put_overwrites_existing_entry():
    client = FakeSupabaseClient()
    service = SearchCacheService(client)
    service.put("query", {"results": [{"title": "old"}]})
    service.put("query", {"results": [{"title": "new"}]})
    assert len(client.search_cache) == 1
    hit = service.get("query")
    assert hit is not None
    assert hit.payload == {"results": [{"title": "new"}]}
