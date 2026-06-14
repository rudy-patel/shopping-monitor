"""Daily digest email job orchestration (T3.6)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from supabase import Client

from core.logging import get_logger
from core.settings import Settings, get_settings
from services.digest_templates import build_digest_email, build_digest_entry
from services.factory import get_mail_service
from services.mail import MailService, MailServiceError
from services.notification_service import RETENTION_DAYS

logger = get_logger(__name__)


@dataclass(frozen=True)
class SendDigestsResult:
    mail_provider: Literal["resend", "noop"]
    users_emailed: int
    users_failed: int
    users_skipped_no_unread: int
    users_skipped_digest_disabled: int
    users_skipped_no_email: int
    notifications_marked_sent: int
    duration_seconds: float


def _retention_cutoff() -> str:
    return (datetime.now(UTC) - timedelta(days=RETENTION_DAYS)).isoformat()


def _load_profiles(client: Client) -> list[dict[str, Any]]:
    result = client.table("profiles").select("user_id,email_digest_enabled").execute()
    return result.data or []


def _load_unsent_notifications(
    client: Client, *, user_id: str, cutoff: str
) -> list[dict[str, Any]]:
    result = (
        client.table("notifications")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_read", False)
        .is_("email_sent_at", "null")
        .gte("created_at", cutoff)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


def _load_product_titles(
    client: Client, product_ids: set[str]
) -> dict[str, str | None]:
    if not product_ids:
        return {}
    result = (
        client.table("products")
        .select("id,title")
        .in_("id", list(product_ids))
        .execute()
    )
    rows = result.data or []
    return {str(row["id"]): row.get("title") for row in rows}


def _resolve_user_email(client: Client, user_id: str) -> str | None:
    try:
        response = client.auth.admin.get_user_by_id(user_id)
    except Exception:
        logger.warning("digest_auth_lookup_failed", extra={"user_id": user_id})
        return None
    user = getattr(response, "user", None)
    if user is None:
        return None
    email = getattr(user, "email", None)
    if not email or not str(email).strip():
        return None
    return str(email).strip()


def _mark_notifications_sent(
    client: Client, notification_ids: list[str], *, sent_at: str
) -> int:
    if not notification_ids:
        return 0
    result = (
        client.table("notifications")
        .update({"email_sent_at": sent_at})
        .in_("id", notification_ids)
        .execute()
    )
    rows = result.data or []
    return len(rows) if isinstance(rows, list) else 0


def run_send_digests(
    client: Client,
    *,
    mail_service: MailService | None = None,
    settings: Settings | None = None,
) -> SendDigestsResult:
    settings = settings or get_settings()
    mail_provider: Literal["resend", "noop"] = (
        "resend" if settings.resend_api_key.strip() else "noop"
    )
    mail = mail_service if mail_service is not None else get_mail_service(settings)

    started = time.perf_counter()
    cutoff = _retention_cutoff()
    profiles = _load_profiles(client)

    users_emailed = 0
    users_failed = 0
    users_skipped_no_unread = 0
    users_skipped_digest_disabled = 0
    users_skipped_no_email = 0
    notifications_marked_sent = 0

    for profile in profiles:
        user_id = str(profile["user_id"])
        if not profile.get("email_digest_enabled", True):
            users_skipped_digest_disabled += 1
            continue

        rows = _load_unsent_notifications(client, user_id=user_id, cutoff=cutoff)
        if not rows:
            users_skipped_no_unread += 1
            continue

        if mail_provider == "noop":
            continue

        to_email = _resolve_user_email(client, user_id)
        if to_email is None:
            users_skipped_no_email += 1
            logger.info("digest_skip_no_email", extra={"user_id": user_id})
            continue

        product_ids = {
            str(row["product_id"]) for row in rows if row.get("product_id") is not None
        }
        titles_by_id = _load_product_titles(client, product_ids)
        entries = [
            build_digest_entry(
                row=row,
                product_title=titles_by_id.get(str(row.get("product_id")))
                if row.get("product_id")
                else None,
                app_base_url=settings.app_base_url,
            )
            for row in rows
        ]
        digest = build_digest_email(to_email=to_email, entries=entries)

        try:
            mail.send_digest(digest)
        except MailServiceError:
            users_failed += 1
            logger.exception("digest_send_failed", extra={"user_id": user_id})
            continue

        sent_at = datetime.now(UTC).isoformat()
        notification_ids = [str(row["id"]) for row in rows]
        marked = _mark_notifications_sent(
            client, notification_ids, sent_at=sent_at
        )
        notifications_marked_sent += marked
        users_emailed += 1

    duration = time.perf_counter() - started
    return SendDigestsResult(
        mail_provider=mail_provider,
        users_emailed=users_emailed,
        users_failed=users_failed,
        users_skipped_no_unread=users_skipped_no_unread,
        users_skipped_digest_disabled=users_skipped_digest_disabled,
        users_skipped_no_email=users_skipped_no_email,
        notifications_marked_sent=notifications_marked_sent,
        duration_seconds=round(duration, 3),
    )
