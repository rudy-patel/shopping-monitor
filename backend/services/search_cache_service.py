"""24-hour search-result cache backed by `public.search_cache` (T8.3)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from postgrest.exceptions import APIError
from supabase import Client

from core.logging import get_logger
from core.settings import Settings, get_settings
from db.supabase_client import response_first_row

logger = get_logger(__name__)


def normalize_query(query: str) -> str:
    """Lowercase, collapse whitespace, strip — used as cache key."""
    return " ".join(query.strip().lower().split())


def hash_query(normalized: str) -> str:
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SearchCacheHit:
    payload: dict[str, Any]
    fetched_at: datetime


class SearchCacheService:
    """Thin Supabase wrapper for the `search_cache` table."""

    def __init__(self, client: Client, *, settings: Settings | None = None) -> None:
        self._client = client
        self._settings = settings or get_settings()

    @property
    def ttl(self) -> timedelta:
        return timedelta(hours=self._settings.search_cache_ttl_hours)

    def get(self, query: str) -> SearchCacheHit | None:
        normalized = normalize_query(query)
        if not normalized:
            return None
        query_hash = hash_query(normalized)

        try:
            result = (
                self._client.table("search_cache")
                .select("*")
                .eq("query_hash", query_hash)
                .maybe_single()
                .execute()
            )
        except APIError as exc:
            logger.warning(
                "search_cache_get_failed",
                extra={"query_hash": query_hash, "error": str(exc)},
            )
            return None
        if result is None:
            return None
        row = response_first_row(result)
        if row is None:
            return None

        fetched_at = _parse_ts(row["fetched_at"])
        if datetime.now(UTC) - fetched_at > self.ttl:
            return None
        payload = row.get("result_payload")
        if not isinstance(payload, dict):
            return None
        return SearchCacheHit(payload=payload, fetched_at=fetched_at)

    def put(self, query: str, payload: dict[str, Any]) -> None:
        normalized = normalize_query(query)
        if not normalized:
            return
        query_hash = hash_query(normalized)
        try:
            # Delete-then-insert keeps it a single round-trip and avoids upsert quirks
            # in older PostgREST/supabase-py combos.
            self._client.table("search_cache").delete().eq(
                "query_hash", query_hash
            ).execute()
            self._client.table("search_cache").insert(
                {
                    "query_hash": query_hash,
                    "query": normalized,
                    "result_payload": payload,
                    "fetched_at": datetime.now(UTC).isoformat(),
                }
            ).execute()
        except APIError as exc:
            # Cache is best-effort — never fail the user request when persistence fails.
            logger.warning(
                "search_cache_put_failed",
                extra={"query_hash": query_hash, "error": str(exc)},
            )


def _parse_ts(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
