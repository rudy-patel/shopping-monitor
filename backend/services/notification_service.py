"""Notification read API and revisit actions (T3.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException
from supabase import Client

from db.supabase_client import get_service_role_client, response_first_row
from services.product_service import update_product

RETENTION_DAYS = 90
DEFAULT_LIMIT = 20
MAX_LIMIT = 50

REVISIT_TYPES = frozenset({"revisit_on_sale", "revisit_stale"})


def get_client() -> Client:
    return get_service_role_client()


def _retention_cutoff() -> str:
    return (datetime.now(UTC) - timedelta(days=RETENTION_DAYS)).isoformat()


def _touch_product_interaction(client: Client, product_id: UUID) -> None:
    client.table("products").update(
        {"last_user_interaction_at": datetime.now(UTC).isoformat()}
    ).eq("id", str(product_id)).execute()


def _get_owned_notification(
    client: Client, *, user_id: UUID, notification_id: UUID
) -> dict[str, Any]:
    result = (
        client.table("notifications")
        .select("*")
        .eq("id", str(notification_id))
        .eq("user_id", str(user_id))
        .maybe_single()
        .execute()
    )
    row = response_first_row(result)
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return row


def _load_products_by_id(
    client: Client, product_ids: set[str]
) -> dict[str, dict[str, Any]]:
    if not product_ids:
        return {}
    result = (
        client.table("products")
        .select("id, title, status")
        .in_("id", list(product_ids))
        .execute()
    )
    rows = result.data or []
    return {str(row["id"]): row for row in rows}


def _enrich_with_product(
    client: Client, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    product_ids = {
        str(row["product_id"]) for row in rows if row.get("product_id") is not None
    }
    products_by_id = _load_products_by_id(client, product_ids)
    enriched: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        product = products_by_id.get(str(product_id)) if (product_id := item.get("product_id")) else None
        item["product_title"] = product.get("title") if product else None
        item["product_status"] = product.get("status") if product else None
        enriched.append(item)
    return enriched


def list_notifications(
    *,
    user_id: UUID,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    unread_only: bool = False,
) -> dict[str, Any]:
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    client = get_client()
    cutoff = _retention_cutoff()

    all_rows_result = (
        client.table("notifications")
        .select("*")
        .eq("user_id", str(user_id))
        .gte("created_at", cutoff)
        .order("created_at", desc=True)
        .execute()
    )
    all_rows = all_rows_result.data or []
    unread_count = sum(1 for row in all_rows if not row.get("is_read"))

    visible_rows = all_rows
    if unread_only:
        visible_rows = [row for row in all_rows if not row.get("is_read")]

    total = len(visible_rows)
    page_rows = visible_rows[offset : offset + limit]
    items = _enrich_with_product(client, page_rows)

    return {
        "items": items,
        "unread_count": unread_count,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def mark_notifications_read(
    *,
    user_id: UUID,
    ids: list[UUID] | None = None,
    all: bool = False,
) -> dict[str, int]:
    if not all and not ids:
        raise HTTPException(status_code=400, detail="Provide ids or all=true")

    client = get_client()
    cutoff = _retention_cutoff()

    if all:
        candidates_result = (
            client.table("notifications")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("is_read", False)
            .gte("created_at", cutoff)
            .execute()
        )
        target_rows = candidates_result.data or []
    else:
        assert ids is not None
        id_strings = [str(notification_id) for notification_id in ids]
        result = (
            client.table("notifications")
            .select("*")
            .eq("user_id", str(user_id))
            .in_("id", id_strings)
            .execute()
        )
        rows = result.data or []
        found_ids = {str(row["id"]) for row in rows}
        missing = [nid for nid in id_strings if nid not in found_ids]
        if missing:
            raise HTTPException(status_code=404, detail="Notification not found")
        target_rows = rows

    updated_count = 0
    touched_products: set[str] = set()
    for row in target_rows:
        if row.get("is_read"):
            continue
        client.table("notifications").update({"is_read": True}).eq(
            "id", row["id"]
        ).execute()
        updated_count += 1
        product_id = row.get("product_id")
        if product_id is not None and str(product_id) not in touched_products:
            _touch_product_interaction(client, UUID(str(product_id)))
            touched_products.add(str(product_id))

    return {"updated_count": updated_count}


def apply_notification_action(
    *,
    user_id: UUID,
    notification_id: UUID,
    action: Literal["keep", "archive"],
) -> dict[str, Any]:
    client = get_client()
    row = _get_owned_notification(
        client, user_id=user_id, notification_id=notification_id
    )
    notification_type = row.get("type")
    if notification_type not in REVISIT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Action not supported for this notification type",
        )

    product_id = row.get("product_id")
    if product_id is None:
        raise HTTPException(status_code=400, detail="Notification has no product")

    product_id_uuid = UUID(str(product_id))

    if action == "archive":
        product_result = (
            client.table("products")
            .select("status")
            .eq("id", str(product_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )
        product = response_first_row(product_result)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        if product.get("status") == "archived":
            raise HTTPException(status_code=400, detail="Product is already archived")
        update_product(
            user_id=user_id,
            product_id=product_id_uuid,
            patch={"status": "archived"},
        )
    else:
        if not row.get("is_read"):
            client.table("notifications").update({"is_read": True}).eq(
                "id", str(notification_id)
            ).execute()
        _touch_product_interaction(client, product_id_uuid)
        return {"notification_id": str(notification_id), "action": action}

    client.table("notifications").update({"is_read": True}).eq(
        "id", str(notification_id)
    ).execute()
    return {"notification_id": str(notification_id), "action": action}
