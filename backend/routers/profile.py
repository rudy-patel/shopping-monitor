"""User profile endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from core.auth import CurrentUser, get_current_user
from services.profile_service import get_or_create_profile, update_profile

router = APIRouter(prefix="/api", tags=["profile"])

DisplayCurrency = Literal["CAD", "USD", "EUR", "GBP"]
Theme = Literal["light", "dark"]


class ProfileResponse(BaseModel):
    user_id: UUID
    display_currency: DisplayCurrency
    default_threshold_pct: int = Field(ge=1, le=95)
    notifications_enabled: bool
    email_digest_enabled: bool
    theme: Theme
    revisit_prompts_enabled: bool
    revisit_on_sale_enabled: bool
    revisit_stale_enabled: bool
    revisit_stale_days: int = Field(ge=7, le=365)
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_currency: DisplayCurrency | None = None
    default_threshold_pct: int | None = Field(default=None, ge=1, le=95)
    notifications_enabled: bool | None = None
    email_digest_enabled: bool | None = None
    theme: Theme | None = None
    revisit_prompts_enabled: bool | None = None
    revisit_on_sale_enabled: bool | None = None
    revisit_stale_enabled: bool | None = None
    revisit_stale_days: int | None = Field(default=None, ge=7, le=365)


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(user: CurrentUser = Depends(get_current_user)) -> ProfileResponse:
    """Return the authenticated user's profile, creating defaults if missing."""
    row = get_or_create_profile(user.user_id)
    return ProfileResponse.model_validate(row)


@router.patch("/profile", response_model=ProfileResponse)
async def patch_profile(
    body: ProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> ProfileResponse:
    """Partially update the authenticated user's profile.

    Validation errors from Pydantic produce HTTP 422.
    """
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        row = update_profile(user.user_id, patch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ProfileResponse.model_validate(row)
