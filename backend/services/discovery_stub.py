"""Background discovery completion stub (T2.5 Option A)."""

from __future__ import annotations

from uuid import UUID

from db.supabase_client import get_service_role_client


def complete_discovery_stub(product_id: UUID) -> None:
    """Mark discovery complete immediately; real discovery deferred to T3.1."""
    client = get_service_role_client()
    client.table("products").update({"discovery_status": "complete"}).eq(
        "id", str(product_id)
    ).execute()
