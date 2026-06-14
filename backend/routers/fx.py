"""Authenticated FX rates endpoint."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import CurrentUser, get_current_user
from services.factory import get_fx_service
from services.fx import CANONICAL_CURRENCY, FxServiceError

router = APIRouter(prefix="/api", tags=["fx"])


class FxRatesResponse(BaseModel):
    base: str
    fetched_at: datetime
    stale: bool
    rates: dict[str, str] = Field(
        description="CAD base rates keyed by ISO currency code; values are decimal strings."
    )


@router.get("/fx/rates", response_model=FxRatesResponse)
async def get_fx_rates(_user: CurrentUser = Depends(get_current_user)) -> FxRatesResponse:
    """Return cached or freshly fetched CAD-based FX rates for display conversion."""
    try:
        result = get_fx_service().fetch_rates()
    except FxServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    fx_rates = result.rates
    stale = result.stale

    rates: dict[str, str] = {CANONICAL_CURRENCY: str(Decimal("1"))}
    for quote, fx_rate in fx_rates.rates.items():
        rates[quote] = str(fx_rate.rate)

    return FxRatesResponse(
        base=fx_rates.base,
        fetched_at=fx_rates.fetched_at,
        stale=stale,
        rates=rates,
    )
