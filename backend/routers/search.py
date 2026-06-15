"""Search API: free-text query → ranked Canadian product candidates (T8.2)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import Client

from core.auth import CurrentUser, get_current_user
from core.logging import get_logger
from db.supabase_client import get_service_role_client
from services.llm import (
    LlmInvalidResponseError,
    LlmProviderError,
    LlmQuotaExhaustedError,
    LlmTimeoutError,
)
from services.search_service import run_search


def get_search_client() -> Client:
    """FastAPI dependency wrapper — keeps the router test-overridable."""
    return get_service_role_client()

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200)


class SearchResultItemResponse(BaseModel):
    title: str
    retailer_slug: str
    retailer_label: str
    url: str
    supported: bool
    brand_hint: str | None = None
    justification: str


class SearchResponseModel(BaseModel):
    query: str
    results: list[SearchResultItemResponse]
    cache_hit: bool
    latency_ms: int


@router.post("/search", response_model=SearchResponseModel)
async def post_search(
    body: SearchRequest,
    user: CurrentUser = Depends(get_current_user),
    client: Client = Depends(get_search_client),
) -> SearchResponseModel:
    """Run a search. Auth required; results are cached globally for 24h."""
    try:
        # Grounded Gemini calls can take 10–30s; keep the event loop responsive.
        result = await asyncio.to_thread(run_search, body.query, client=client)
    except LlmQuotaExhaustedError as exc:
        # Daily Gemini free-tier quota — retrying just burns more quota. Use 429 so
        # the frontend can show a specific "daily limit" message and stop retrying.
        logger.warning("search_quota_exhausted", extra={"error": str(exc)})
        raise HTTPException(
            status_code=429,
            detail=(
                "Daily AI search limit reached. Try again later, "
                "or paste a product URL directly to add it now."
            ),
        ) from exc
    except LlmTimeoutError as exc:
        logger.warning("search_timeout", extra={"error": str(exc)})
        raise HTTPException(
            status_code=504,
            detail="Search took too long. Try a more specific query.",
        ) from exc
    except LlmInvalidResponseError as exc:
        logger.warning("search_invalid_response", extra={"error": str(exc)})
        raise HTTPException(
            status_code=502,
            detail="Search response was malformed. Please try again.",
        ) from exc
    except LlmProviderError as exc:
        logger.warning("search_provider_error", extra={"error": str(exc)})
        raise HTTPException(
            status_code=503,
            detail="Search is temporarily unavailable. Please try again in a moment.",
        ) from exc

    return SearchResponseModel.model_validate(result.to_dict())
