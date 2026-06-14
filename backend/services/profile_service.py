"""Profile persistence backed by the service-role Supabase client."""

from __future__ import annotations

from uuid import UUID

from postgrest.exceptions import APIError
from supabase import Client

from core.logging import get_logger
from db.supabase_client import get_service_role_client

logger = get_logger(__name__)

PROFILE_COLUMNS: tuple[str, ...] = (
    "user_id",
    "display_currency",
    "default_threshold_pct",
    "notifications_enabled",
    "email_digest_enabled",
    "theme",
    "revisit_prompts_enabled",
    "revisit_on_sale_enabled",
    "revisit_stale_enabled",
    "revisit_stale_days",
    "created_at",
    "updated_at",
)

PROFILE_DEFAULTS: dict[str, object] = {
    "display_currency": "CAD",
    "default_threshold_pct": 20,
    "notifications_enabled": True,
    "email_digest_enabled": True,
    "theme": "light",
    "revisit_prompts_enabled": True,
    "revisit_on_sale_enabled": True,
    "revisit_stale_enabled": True,
    "revisit_stale_days": 30,
}


def get_client() -> Client:
    return get_service_role_client()


def _is_duplicate_key_error(exc: APIError) -> bool:
    code = getattr(exc, "code", None)
    if code == "23505":
        return True
    message = str(exc).lower()
    return "duplicate key" in message or "23505" in message


def get_or_create_profile(user_id: UUID) -> dict:
    client = get_client()
    user_id_str = str(user_id)

    existing = (
        client.table("profiles")
        .select(",".join(PROFILE_COLUMNS))
        .eq("user_id", user_id_str)
        .limit(1)
        .maybe_single()
        .execute()
    )
    if existing.data is not None:
        return existing.data

    try:
        inserted = (
            client.table("profiles")
            .insert({**PROFILE_DEFAULTS, "user_id": user_id_str})
            .select(",".join(PROFILE_COLUMNS))
            .single()
            .execute()
        )
    except APIError as exc:
        if not _is_duplicate_key_error(exc):
            raise
        logger.debug(
            "profile_insert_race",
            extra={"user_id": user_id_str},
        )
        raced = (
            client.table("profiles")
            .select(",".join(PROFILE_COLUMNS))
            .eq("user_id", user_id_str)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if raced.data is None:
            raise
        return raced.data

    logger.info("profile_created", extra={"user_id": user_id_str})
    return inserted.data


def update_profile(user_id: UUID, patch: dict) -> dict:
    if not patch:
        raise ValueError("No fields to update")

    client = get_client()
    user_id_str = str(user_id)

    updated = (
        client.table("profiles")
        .update(patch)
        .eq("user_id", user_id_str)
        .select(",".join(PROFILE_COLUMNS))
        .single()
        .execute()
    )
    if updated.data is not None:
        logger.info("profile_updated", extra={"user_id": user_id_str})
        return updated.data

    get_or_create_profile(user_id)
    updated = (
        client.table("profiles")
        .update(patch)
        .eq("user_id", user_id_str)
        .select(",".join(PROFILE_COLUMNS))
        .single()
        .execute()
    )
    logger.info("profile_updated", extra={"user_id": user_id_str})
    return updated.data
