"""Internal worker job endpoints (T3.5)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from core.security import require_worker_token
from db.supabase_client import get_service_role_client
from services.scrape_job_service import ScrapeAllResult, run_scrape_all

router = APIRouter(tags=["internal"])


@router.post("/internal/jobs/scrape-all", response_model=ScrapeAllResult)
async def scrape_all(_: None = Depends(require_worker_token)) -> ScrapeAllResult:
    client = get_service_role_client()
    return run_scrape_all(client)
