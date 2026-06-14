"""Account deletion via Supabase Auth admin API (DB cascades handle app data)."""

from __future__ import annotations

from uuid import UUID

from core.logging import get_logger
from core.protected_accounts import assert_safe_to_delete
from db.supabase_client import get_service_role_client

logger = get_logger(__name__)


class AccountNotFoundError(Exception):
    """Auth user does not exist."""


class AccountProtectedError(Exception):
    """Hard-denied identity (dev bypass user, protected email)."""


class AccountDeleteError(Exception):
    """Supabase Auth admin delete failed."""


def _auth_user_exists(user_id_str: str) -> bool:
    client = get_service_role_client()
    try:
        response = client.auth.admin.get_user_by_id(user_id_str)
    except Exception:
        return False
    return getattr(response, "user", None) is not None


def delete_account(user_id: UUID, *, email: str | None = None) -> None:
    """Delete the auth user; Postgres ON DELETE CASCADE removes app-owned rows."""
    user_id_str = str(user_id)

    try:
        assert_safe_to_delete(user_id=user_id_str, email=email)
    except RuntimeError as exc:
        raise AccountProtectedError(str(exc)) from exc

    if not _auth_user_exists(user_id_str):
        raise AccountNotFoundError(user_id_str)

    client = get_service_role_client()
    try:
        client.auth.admin.delete_user(user_id_str)
    except Exception as exc:
        raise AccountDeleteError(user_id_str) from exc

    logger.info("account_deleted", extra={"user_id": user_id_str})
