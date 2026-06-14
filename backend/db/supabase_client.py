"""Minimal Supabase client helpers for health checks."""

from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from core.settings import clear_settings_cache, get_settings

_logger = logging.getLogger(__name__)


def response_first_row(response: Any) -> dict | None:
    """Return the first row from a PostgREST API response."""
    if response is None:
        return None
    data = getattr(response, "data", None)
    if data is None:
        return None
    if isinstance(data, list):
        return data[0] if data else None
    if isinstance(data, dict):
        return data
    return None


@lru_cache(maxsize=1)
def get_service_role_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError(
            "Supabase service-role client requires SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY"
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def reset_service_role_client_cache() -> None:
    get_service_role_client.cache_clear()
    clear_settings_cache()


def get_supabase_health() -> dict[str, Any]:
    """Return connectivity status. Graceful when env vars are unset."""
    try:
        client = get_service_role_client()
    except RuntimeError:
        return {
            "healthy": False,
            "latency_ms": None,
            "error": "Supabase not configured (set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)",
            "details": None,
        }

    settings = get_settings()
    try:
        started = time.perf_counter()
        # Lightweight round-trip; works even before app tables exist.
        client.table("_nonexistent_health_probe").select("*").limit(1).execute()
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return {
            "healthy": True,
            "latency_ms": latency_ms,
            "error": None,
            "details": {"url": settings.supabase_url},
        }
    except Exception as exc:  # noqa: BLE001 — surface any connectivity failure
        _logger.debug("Supabase health check failed: %s", exc)
        message = str(exc)
        # PostgREST returns 404/42P01 for missing tables — still means API is reachable.
        if "does not exist" in message.lower() or "42p01" in message.lower():
            return {
                "healthy": True,
                "latency_ms": None,
                "error": None,
                "details": {
                    "url": settings.supabase_url,
                    "note": "connected (no probe table)",
                },
            }
        return {
            "healthy": False,
            "latency_ms": None,
            "error": message,
            "details": None,
        }
