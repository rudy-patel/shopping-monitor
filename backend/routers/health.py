"""Health-check endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from db.supabase_client import get_supabase_health

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
