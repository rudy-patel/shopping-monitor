"""Health-check endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter

from core.logging import get_logger
from core.settings import get_settings
from db.supabase_client import get_supabase_health

logger = get_logger(__name__)

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Shopping Monitor API is running"}


@router.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    """Liveness probe for dev scripts and deployment monitors."""
    supabase_health = get_supabase_health()
    db_connected = supabase_health.get("healthy", False)

    return {
        "status": "healthy" if db_connected else "degraded",
        "service": "shopping-monitor-api",
        "database": {
            "status": "connected" if db_connected else "disconnected",
            "latency_ms": supabase_health.get("latency_ms"),
            "error": supabase_health.get("error"),
        },
        "version": "0.1.0",
    }


@router.get("/health/supabase")
async def supabase_health_check():
    """Detailed Supabase connectivity check."""
    return get_supabase_health()


@router.get("/health/llm")
async def llm_health_check():
    """Diagnose Gemini configuration without burning grounded-search quota.

    Returns whether the API key is configured + which models are wired. Does NOT
    call Gemini — production debugging only needs to know if the env is set up.
    To verify a live call, run `backend/scripts/smoke_search_live.py --live`.
    """
    settings = get_settings()
    has_key = bool(settings.gemini_api_key.strip())
    return {
        "configured": has_key,
        "categorize_model": settings.gemini_model,
        "search_model": settings.gemini_search_model,
        "search_timeout_s": settings.gemini_search_timeout_s,
        "discover_timeout_s": settings.gemini_discover_timeout_s,
        "scraper_mode": settings.scraper_mode,
        "checked_at": int(time.time()),
    }
