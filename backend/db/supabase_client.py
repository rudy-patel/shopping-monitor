"""Minimal Supabase client helpers for health checks."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()

_logger = logging.getLogger(__name__)


def _strip_env(name: str) -> str:
    return (os.getenv(name) or "").strip()


SUPABASE_URL = _strip_env("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = _strip_env("SUPABASE_SERVICE_ROLE_KEY")


def get_supabase_health() -> dict[str, Any]:
    """Return connectivity status. Graceful when env vars are unset."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return {
            "healthy": False,
            "latency_ms": None,
            "error": "Supabase not configured (set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)",
            "details": None,
        }

    try:
        from supabase import create_client

        client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        started = time.perf_counter()
        # Lightweight round-trip; works even before app tables exist.
        client.table("_nonexistent_health_probe").select("*").limit(1).execute()
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return {
            "healthy": True,
            "latency_ms": latency_ms,
            "error": None,
            "details": {"url": SUPABASE_URL},
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
                "details": {"url": SUPABASE_URL, "note": "connected (no probe table)"},
            }
        return {
            "healthy": False,
            "latency_ms": None,
            "error": message,
            "details": None,
        }
