"""Shared price-history observation loading."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from supabase import Client

from services.pricing import ListingDailyObservation


def _parse_ts(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def load_price_observations(
    client: Client,
    listings: list[dict[str, Any]],
    *,
    today: date,
    window_days: int = 30,
) -> list[ListingDailyObservation]:
    if not listings:
        return []
    listing_ids = [row["id"] for row in listings]
    listing_by_id = {row["id"]: row for row in listings}
    window_start = today - timedelta(days=window_days)
    history = (
        client.table("price_history")
        .select("listing_id,price_cents,is_in_stock,observed_at")
        .in_("listing_id", listing_ids)
        .execute()
    )
    observations: list[ListingDailyObservation] = []
    for row in history.data or []:
        observed_at = _parse_ts(row["observed_at"])
        if observed_at is None:
            continue
        observed_on = observed_at.date()
        if observed_on < window_start or observed_on > today:
            continue
        listing = listing_by_id.get(row["listing_id"])
        if listing is None:
            continue
        observations.append(
            ListingDailyObservation(
                listing_id=UUID(row["listing_id"]),
                observed_on=observed_on,
                price_cents=row["price_cents"],
                is_in_stock=row.get("is_in_stock")
                if row.get("is_in_stock") is not None
                else bool(listing.get("is_in_stock")),
                review_status=listing["review_status"],
                is_primary=bool(listing.get("is_primary")),
            )
        )
    return observations
