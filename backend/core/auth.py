"""Supabase JWT validation and auth-bypass dev dependency."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, Field

from core.logging import get_logger
from core.settings import Settings, get_settings

logger = get_logger(__name__)

_jwks_clients: dict[str, jwt.PyJWKClient] = {}


class _InvalidToken(Exception):
    pass


class CurrentUser(BaseModel):
    user_id: UUID
    email: str | None = None
    role: str | None = None
    raw_claims: dict[str, Any] = Field(default_factory=dict)


def _jwks_url(settings: Settings) -> str:
    return f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


def _get_jwks_client(settings: Settings) -> jwt.PyJWKClient:
    url = _jwks_url(settings)
    if url not in _jwks_clients:
        _jwks_clients[url] = jwt.PyJWKClient(url, cache_keys=True)
    return _jwks_clients[url]


def clear_jwks_client_cache() -> None:
    _jwks_clients.clear()


def _decode_jwt(token: str, settings: Settings) -> dict[str, Any]:
    try:
        signing_key = _get_jwks_client(settings).get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            leeway=30,
        )
    except (jwt.PyJWTError, jwt.PyJWKClientError) as exc:
        raise _InvalidToken from exc


async def get_current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if settings.auth_bypass_enabled:
        logger.debug(
            "auth_bypass_active",
            extra={"dev_user_id": str(settings.dev_user_id)},
        )
        return CurrentUser(
            user_id=settings.dev_user_id,
            email="dev@local.test",
            role="authenticated",
            raw_claims={
                "sub": str(settings.dev_user_id),
                "aud": "authenticated",
                "role": "authenticated",
            },
        )

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = _decode_jwt(token, settings)
    except _InvalidToken:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(sub)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    return CurrentUser(
        user_id=user_id,
        email=claims.get("email"),
        role=claims.get("role"),
        raw_claims=claims,
    )
