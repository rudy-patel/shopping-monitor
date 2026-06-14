"""Notification API endpoints (T3.3)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from core.auth import CurrentUser, get_current_user
from services.notification_service import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    apply_notification_action,
    list_notifications,
    mark_notifications_read,
)

router = APIRouter(prefix="/api", tags=["notifications"])

NotificationType = Literal[
    "price_drop",
    "back_in_stock",
    "discovery_complete",
    "needs_input",
    "scrape_failing",
    "revisit_on_sale",
    "revisit_stale",
]


class NotificationItem(BaseModel):
    id: UUID
    user_id: UUID
    product_id: UUID | None = None
    listing_id: UUID | None = None
    type: NotificationType
    payload: dict[str, Any] = Field(default_factory=dict)
    is_read: bool
    email_sent_at: datetime | None = None
    created_at: datetime
    product_title: str | None = None
    product_status: str | None = None


class NotificationsListResponse(BaseModel):
    items: list[NotificationItem]
    unread_count: int
    total: int
    limit: int
    offset: int


class MarkReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids: list[UUID] | None = None
    all: bool = False


class MarkReadResponse(BaseModel):
    updated_count: int


class NotificationActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["keep", "archive"]


class NotificationActionResponse(BaseModel):
    notification_id: UUID
    action: Literal["keep", "archive"]


@router.get("/notifications", response_model=NotificationsListResponse)
async def get_notifications(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False),
    user: CurrentUser = Depends(get_current_user),
) -> NotificationsListResponse:
    """List notifications for the authenticated user (90-day window)."""
    result = list_notifications(
        user_id=user.user_id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )
    return NotificationsListResponse.model_validate(result)


@router.post("/notifications/mark-read", response_model=MarkReadResponse)
async def post_mark_read(
    body: MarkReadRequest,
    user: CurrentUser = Depends(get_current_user),
) -> MarkReadResponse:
    """Mark one or more notifications as read."""
    if not body.all and not body.ids:
        raise HTTPException(status_code=400, detail="Provide ids or all=true")

    result = mark_notifications_read(
        user_id=user.user_id,
        ids=body.ids,
        all=body.all,
    )
    return MarkReadResponse.model_validate(result)


@router.post(
    "/notifications/{notification_id}/action",
    response_model=NotificationActionResponse,
)
async def post_notification_action(
    notification_id: UUID,
    body: NotificationActionRequest,
    user: CurrentUser = Depends(get_current_user),
) -> NotificationActionResponse:
    """Handle revisit keep/archive actions."""
    result = apply_notification_action(
        user_id=user.user_id,
        notification_id=notification_id,
        action=body.action,
    )
    return NotificationActionResponse.model_validate(result)
