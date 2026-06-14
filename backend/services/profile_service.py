"""Profile persistence backed by the service-role Supabase client."""

from __future__ import annotations

from uuid import UUID

from postgrest.exceptions import APIError
from supabase import Client

from core.logging import get_logger
from db.supabase_client import get_service_role_client, response_first_row

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


def _is_not_found_error(exc: APIError) -> bool:
    code = getattr(exc, "code", None)
    if code == "PGRST116":
        return True
    message = str(exc).lower()
    return "0 rows" in message or "pgrst116" in message


def _select_profile(client: Client, user_id_str: str) -> dict | None:
    result = (
        client.table("profiles")
        .select(",".join(PROFILE_COLUMNS))
        .eq("user_id", user_id_str)
        .limit(1)
        .maybe_single()
        .execute()
    )
    if result is None:
        return None
    return result.data


def _apply_profile_update(client: Client, user_id_str: str, patch: dict) -> dict:
    updated = (
        client.table("profiles")
        .update(patch)
        .eq("user_id", user_id_str)
        .select(",".join(PROFILE_COLUMNS))
        .execute()
    )
    row = response_first_row(updated)
    if row is None:
        raise APIError({"message": "Row not found", "code": "PGRST116"})
    return row


def get_or_create_profile(user_id: UUID) -> dict:
    client = get_client()
    user_id_str = str(user_id)

    existing = _select_profile(client, user_id_str)
    if existing is not None:
        return existing

    try:
        inserted = (
            client.table("profiles")
            .insert({**PROFILE_DEFAULTS, "user_id": user_id_str})
            .select(",".join(PROFILE_COLUMNS))
            .execute()
        )
    except APIError as exc:
        if not _is_duplicate_key_error(exc):
            raise
        logger.debug(
            "profile_insert_race",
            extra={"user_id": user_id_str},
        )
        raced = _select_profile(client, user_id_str)
        if raced is None:
            raise
        return raced

    row = response_first_row(inserted)
    if row is None:
        raise RuntimeError(f"Profile insert returned no row for user_id={user_id_str}")

    logger.info("profile_created", extra={"user_id": user_id_str})
    return row


def update_profile(user_id: UUID, patch: dict) -> dict:
    if not patch:
        raise ValueError("No fields to update")

    client = get_client()
    user_id_str = str(user_id)

    try:
        row = _apply_profile_update(client, user_id_str, patch)
    except APIError as exc:
        if not _is_not_found_error(exc):
            raise
        get_or_create_profile(user_id)
        row = _apply_profile_update(client, user_id_str, patch)

    logger.info("profile_updated", extra={"user_id": user_id_str})
    return row
