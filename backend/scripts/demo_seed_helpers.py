"""Pure helpers for production demo seed (unit-testable, no live I/O)."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from services.pricing import MIN_TREND_HISTORY_DAYS, TrendDirection, compute_trend, ListingDailyObservation

Trend = Literal["down", "up", "same"]

VALID_CATEGORIES = frozenset({"clothing", "shoes", "home", "tech", "other"})
VALID_STATUSES = frozenset({"active", "needs_input", "archived"})
VALID_TRENDS = frozenset({"down", "up", "same"})
VALID_NOTIFICATION_TYPES = frozenset(
    {
        "price_drop",
        "back_in_stock",
        "discovery_complete",
        "needs_input",
        "scrape_failing",
        "revisit_on_sale",
        "revisit_stale",
    }
)

CATALOG_PATH = Path(__file__).with_name("demo_catalog.prod.json")


def price_for_day(
    *,
    day_offset: int,
    total_days: int,
    current_cents: int,
    trend: Trend,
) -> int:
    """Synthetic daily price ending at current_cents on the last day."""
    if total_days <= 1:
        return current_cents

    progress = day_offset / (total_days - 1)
    if trend == "down":
        start = int(current_cents * 1.22)
        price = int(start + (current_cents - start) * progress)
    elif trend == "up":
        start = int(current_cents * 0.88)
        price = int(start + (current_cents - start) * progress)
    else:
        wiggle = [0, 1, -1, 0, 1, -1, 0][day_offset % 7]
        price = int(current_cents * (1 + wiggle * 0.01))
    return max(price, 100)


def build_price_history_rows(
    *,
    listing_id: str,
    current_cents: int,
    trend: Trend,
    days: int,
    end_date: date,
    in_stock: bool = True,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for offset in range(days):
        observed_on = end_date - timedelta(days=days - 1 - offset)
        price = price_for_day(
            day_offset=offset,
            total_days=days,
            current_cents=current_cents,
            trend=trend,
        )
        observed_at = datetime.combine(observed_on, datetime.min.time(), tzinfo=UTC).replace(
            hour=8
        )
        rows.append(
            {
                "listing_id": listing_id,
                "price_cents": price,
                "is_in_stock": in_stock,
                "observed_at": observed_at.isoformat(),
                "source": "scheduled" if offset % 5 else "manual",
            }
        )
    return rows


def scrape_snapshot(
    *,
    title: str,
    brand: str | None,
    price_cents: int,
    in_stock: bool = True,
) -> dict[str, Any]:
    return {
        "title": title,
        "brand": brand,
        "price_cents": price_cents,
        "is_in_stock": in_stock,
        "breadcrumbs": [],
        "raw_snapshot": {},
    }


def assert_prod_safe(catalog: dict[str, Any]) -> None:
    blob = json.dumps(catalog)
    if "fixtures.local" in blob:
        raise RuntimeError("Catalog contains fixtures.local URLs — not allowed for prod.")


def validate_catalog(catalog: dict[str, Any]) -> None:
    """Raise ValueError when catalog shape/content is invalid."""
    assert_prod_safe(catalog)

    products = catalog.get("products")
    if not isinstance(products, list) or not products:
        raise ValueError("catalog.products must be a non-empty list")

    keys: set[str] = set()
    for spec in products:
        key = spec.get("key")
        if not key or key in keys:
            raise ValueError(f"duplicate or missing product key: {key!r}")
        keys.add(key)

        if spec.get("category") not in VALID_CATEGORIES:
            raise ValueError(f"{key}: invalid category {spec.get('category')!r}")
        if spec.get("status") not in VALID_STATUSES:
            raise ValueError(f"{key}: invalid status {spec.get('status')!r}")
        if spec.get("trend") not in VALID_TRENDS:
            raise ValueError(f"{key}: invalid trend {spec.get('trend')!r}")

        listings = spec.get("listings")
        if not isinstance(listings, list) or not listings:
            raise ValueError(f"{key}: must have at least one listing")

        primary_count = sum(1 for row in listings if row.get("is_primary"))
        if len(listings) == 1 and primary_count == 0:
            pass  # single listing defaults to primary in seed script
        elif primary_count != 1:
            raise ValueError(f"{key}: expected exactly one is_primary listing")

        for listing in listings:
            url = str(listing.get("url", ""))
            if not url.startswith("https://"):
                raise ValueError(f"{key}: listing URL must be https: {url!r}")

    for note in catalog.get("notifications", []):
        note_type = note.get("type")
        if note_type not in VALID_NOTIFICATION_TYPES:
            raise ValueError(f"invalid notification type: {note_type!r}")
        if note.get("product_key") not in keys:
            raise ValueError(f"notification references unknown product_key: {note.get('product_key')!r}")


def listing_is_primary(listing_spec: dict[str, Any], *, listing_count: int) -> bool:
    if "is_primary" in listing_spec:
        return bool(listing_spec["is_primary"])
    return listing_count == 1


def trend_direction_for_series(
    *,
    rows: list[dict[str, Any]],
    listing_id: str,
    today: date,
) -> TrendDirection:
    observations = [
        ListingDailyObservation(
            listing_id=listing_id,
            observed_on=datetime.fromisoformat(row["observed_at"]).date(),
            price_cents=int(row["price_cents"]),
            is_in_stock=bool(row["is_in_stock"]),
            review_status="accepted",
            is_primary=True,
        )
        for row in rows
    ]
    return compute_trend(observations, today=today).direction


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    catalog_path = path or CATALOG_PATH
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    validate_catalog(catalog)
    return catalog


def history_days_for_product(*, status: str, created_days_ago: int, archived_days_ago: int) -> int:
    if status == "active":
        return max(MIN_TREND_HISTORY_DAYS + 1, 32)
    return max(MIN_TREND_HISTORY_DAYS + 1, created_days_ago - archived_days_ago)
