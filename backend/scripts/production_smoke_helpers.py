"""Pure helpers for T6.2 production smoke (unit-testable, no live I/O)."""

from __future__ import annotations

import json
from typing import Any

VALID_CATEGORIES = frozenset({"tech", "fashion", "home", "sports", "other"})

RETAILERS = (
    {
        "slug": "bestbuy_ca",
        "url": "https://www.bestbuy.ca/en-ca/product/nintendo-switch-2-console/19296507",
    },
    {
        "slug": "palmisleskate",
        "url": "https://palmisleskateshop.com/products/bones-reds-bearings",
    },
)


def primary_listing(body: dict[str, Any]) -> dict[str, Any] | None:
    listings = body.get("listings") or []
    return next((row for row in listings if row.get("is_primary")), None)


def listing_price_cents(listing: dict[str, Any]) -> int | None:
    value = listing.get("last_known_price_cents") or listing.get("price_cents")
    return int(value) if value is not None else None


def validate_add_response(
    body: dict[str, Any],
    *,
    expected_retailer: str,
    max_seconds: float,
    elapsed: float,
) -> None:
    if elapsed > max_seconds:
        raise RuntimeError(f"add exceeded {max_seconds}s ({elapsed:.2f}s)")

    listing = primary_listing(body)
    if not listing or listing.get("scrape_status") != "ok":
        raise RuntimeError(f"listing scrape_status not ok: {json.dumps(body, indent=2)}")

    if listing.get("retailer_slug") != expected_retailer:
        raise RuntimeError(
            f"expected retailer {expected_retailer!r}, got {listing.get('retailer_slug')!r}"
        )

    price_cents = listing_price_cents(listing)
    if not body.get("title") or not price_cents:
        raise RuntimeError(f"missing title/price: {json.dumps(body, indent=2)}")

    if body.get("category") not in VALID_CATEGORIES:
        raise RuntimeError(f"unexpected category: {body.get('category')!r}")


def summarize_add_result(
    body: dict[str, Any],
    *,
    retailer: str,
    url: str,
    elapsed: float,
    refresh_status: int,
) -> dict[str, Any]:
    listing = primary_listing(body) or {}
    return {
        "retailer": retailer,
        "url": url,
        "product_id": str(body["id"]),
        "add_seconds": round(elapsed, 3),
        "title": body.get("title"),
        "category": body.get("category"),
        "category_source": body.get("category_source"),
        "price_cents": listing_price_cents(listing),
        "refresh_status": refresh_status,
        "refresh_ok": refresh_status in {200, 429},
    }
