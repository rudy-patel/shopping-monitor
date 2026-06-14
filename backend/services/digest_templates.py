"""Plain text and HTML digest templates (T3.6). Copy mirrors NotificationRow.tsx."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import HttpUrl

from services.mail import DigestEmail, DigestNotificationEntry
from services.notifications import NotificationKind

DIGEST_SUBJECT = "Your Shopping Monitor digest"

_RETAILER_LABELS: dict[str, str] = {
    "bestbuy_ca": "Best Buy Canada",
    "indigo": "Indigo",
    "apple_ca": "Apple Canada",
    "abercrombie": "Abercrombie & Fitch",
    "palmisleskate": "Palm Isle Skate Shop",
    "tikiroomskate": "Tiki Room Skateboards",
    "generic": "Generic scraper — may be unreliable",
}

_REVISIT_TYPES = frozenset(
    {NotificationKind.REVISIT_ON_SALE, NotificationKind.REVISIT_STALE}
)


def _retailer_label(slug: str | None) -> str:
    if not slug:
        return "Unknown retailer"
    return _RETAILER_LABELS.get(slug, slug.replace("_", " "))


def format_cad_cents(cents: int) -> str:
    """Display-only CAD formatting for digest copy (stored values remain CAD)."""
    dollars = cents / 100
    return f"${dollars:,.2f}"


def notification_deep_link(
    *,
    app_base_url: str,
    notification_type: NotificationKind,
    product_id: UUID | None,
) -> str:
    base = app_base_url.rstrip("/")
    if notification_type in _REVISIT_TYPES:
        return f"{base}/notifications"
    if notification_type == NotificationKind.NEEDS_INPUT and product_id is not None:
        return f"{base}/products/{product_id}/variants"
    if product_id is not None:
        return f"{base}/products/{product_id}"
    return f"{base}/notifications"


def notification_summary(
    *,
    notification_type: NotificationKind,
    product_title: str | None,
    payload: dict[str, Any],
) -> str:
    title = product_title or "A product"
    match notification_type:
        case NotificationKind.DISCOVERY_COMPLETE:
            auto_added = int(payload.get("auto_added_count") or 0)
            needs_review = int(payload.get("needs_review_count") or 0)
            name = product_title or "this product"
            if needs_review > 0:
                return (
                    f"Found {auto_added + needs_review} matches for {name}. "
                    f"{needs_review} need your review."
                )
            plural = "" if auto_added == 1 else "es"
            return f"Found {auto_added} new retailer match{plural} for {name}."
        case NotificationKind.NEEDS_INPUT:
            name = product_title or "this product"
            return f"Choose a variant for {name}."
        case NotificationKind.PRICE_DROP:
            old_price = int(payload.get("old_price_cents") or 0)
            new_price = int(payload.get("new_price_cents") or 0)
            return (
                f"{title} dropped from {format_cad_cents(old_price)} "
                f"to {format_cad_cents(new_price)}."
            )
        case NotificationKind.BACK_IN_STOCK:
            retailer = _retailer_label(str(payload.get("retailer_slug") or ""))
            return f"{title} is back in stock at {retailer}."
        case NotificationKind.SCRAPE_FAILING:
            return (
                f"We could not refresh prices for {title}. "
                "We will keep trying on the daily check."
            )
        case NotificationKind.REVISIT_ON_SALE:
            name = product_title or "this item"
            return (
                f"{name} has been on your list a while and is on sale now. "
                "Still want it?"
            )
        case NotificationKind.REVISIT_STALE:
            name = product_title or "this item"
            return (
                f"{name} has been sitting on your list without much attention. "
                "Ready to let it go?"
            )
        case _:
            return "Update available."


def build_digest_entry(
    *,
    row: dict[str, Any],
    product_title: str | None,
    app_base_url: str,
) -> DigestNotificationEntry:
    notification_type = NotificationKind(str(row["type"]))
    product_id = UUID(str(row["product_id"])) if row.get("product_id") else None
    payload = row.get("payload") or {}
    summary = notification_summary(
        notification_type=notification_type,
        product_title=product_title,
        payload=payload,
    )
    link = notification_deep_link(
        app_base_url=app_base_url,
        notification_type=notification_type,
        product_id=product_id,
    )
    created_at = row["created_at"]
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return DigestNotificationEntry(
        notification_id=UUID(str(row["id"])),
        type=notification_type,
        product_id=product_id,
        product_title=product_title or "A product",
        summary=summary,
        deep_link=HttpUrl(link),
        created_at=created_at,
    )


def render_digest_text(entries: list[DigestNotificationEntry]) -> str:
    lines = [
        "Your unread Shopping Monitor updates:",
        "",
    ]
    for entry in entries:
        lines.append(f"- {entry.summary}")
        lines.append(f"  {entry.deep_link}")
        lines.append("")
    lines.append("Open the app for revisit prompts and more details.")
    return "\n".join(lines).rstrip() + "\n"


def render_digest_html(entries: list[DigestNotificationEntry]) -> str:
    items = []
    for entry in entries:
        items.append(
            "<li>"
            f"<p>{_escape_html(entry.summary)}</p>"
            f'<p><a href="{_escape_html(str(entry.deep_link))}">View in app</a></p>'
            "</li>"
        )
    body = (
        "<p>Your unread Shopping Monitor updates:</p>"
        f"<ul>{''.join(items)}</ul>"
        "<p>Open the app for revisit prompts and more details.</p>"
    )
    return f"<!DOCTYPE html><html><body>{body}</body></html>"


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_digest_email(
    *,
    to_email: str,
    entries: list[DigestNotificationEntry],
) -> DigestEmail:
    return DigestEmail(
        to_email=to_email,
        subject=DIGEST_SUBJECT,
        text_body=render_digest_text(entries),
        html_body=render_digest_html(entries),
        entries=entries,
    )
