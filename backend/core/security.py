"""Security dependencies for internal endpoints."""

from __future__ import annotations

import hmac

from fastapi import Depends, Header, HTTPException

from core.settings import Settings, get_settings


async def require_worker_token(
    x_worker_token: str | None = Header(default=None, alias="X-Worker-Token"),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.worker_token:
        raise HTTPException(status_code=503, detail="Worker token not configured")
    if not x_worker_token or not hmac.compare_digest(
        x_worker_token, settings.worker_token
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing worker token")
