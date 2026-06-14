"""Post-scrape notification evaluation orchestration (T3.4)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from supabase import Client

from services.notifications import (
    ListingNotificationSnapshot,
    NotificationEvaluationContext,
    NotificationProposal,
    ProductNotificationSnapshot,
    ProfileNotificationFlags,
    RecentNotificationRow,
    default_composite_evaluator,
)
from services.pricing_data import load_price_observations
from services.profile_service import get_or_create_profile

__all__ = [
    "build_evaluation_context",
    "evaluate_product_notifications",
    "load_recent_notifications",
    "persist_proposals",
    "run_post_scrape_evaluation",
    "run_revisit_evaluation_for_active_products",
]


def _parse_ts(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _effective_threshold_pct(product: dict[str, Any], profile: dict[str, Any]) -> int:
    threshold = product.get("notification_threshold_pct")
    if threshold is not None:
        return int(threshold)
    return int(profile["default_threshold_pct"])


def load_recent_notifications(
    client: Client,
    user_id: UUID,
    product_id: UUID,
    *,
    lookback_days: int = 30,
    as_of: datetime | None = None,
) -> list[RecentNotificationRow]:
    as_of = as_of or datetime.now(UTC)
    cutoff = (as_of - timedelta(days=lookback_days)).isoformat()
    result = (
        client.table("notifications")
        .select("type,product_id,listing_id,created_at")
        .eq("user_id", str(user_id))
        .eq("product_id", str(product_id))
        .gte("created_at", cutoff)
        .execute()
    )
    rows: list[RecentNotificationRow] = []
    for row in result.data or []:
        created_at = _parse_ts(row.get("created_at"))
        if created_at is None:
            continue
        listing_id = row.get("listing_id")
        product_row_id = row.get("product_id")
        rows.append(
            RecentNotificationRow(
                type=row["type"],
                product_id=UUID(product_row_id) if product_row_id else None,
                listing_id=UUID(listing_id) if listing_id else None,
                created_at=created_at,
            )
        )
    return rows


def build_evaluation_context(
    *,
    client: Client,
    user_id: UUID,
    product: dict[str, Any],
    profile: dict[str, Any],
    listings: list[dict[str, Any]],
    listings_before: dict[str, dict[str, Any]],
    evaluated_at: datetime,
    scrape_source: Literal["scheduled", "manual"],
    today: date | None = None,
) -> NotificationEvaluationContext:
    today = today or evaluated_at.date()
    listing_snapshots: list[ListingNotificationSnapshot] = []
    for row in listings:
        before = listings_before.get(str(row["id"]), {})
        listing_snapshots.append(
            ListingNotificationSnapshot(
                id=UUID(str(row["id"])),
                retailer_slug=row["retailer_slug"],
                is_in_stock=row.get("is_in_stock"),
                previous_is_in_stock=before.get("is_in_stock"),
                scrape_failure_count=int(row.get("scrape_failure_count") or 0),
                review_status=row["review_status"],
                is_primary=bool(row.get("is_primary")),
            )
        )

    created_at = _parse_ts(product.get("created_at"))
    if created_at is None:
        created_at = evaluated_at

    return NotificationEvaluationContext(
        user_id=user_id,
        product_id=UUID(str(product["id"])),
        evaluated_at=evaluated_at,
        scrape_source=scrape_source,
        effective_threshold_pct=_effective_threshold_pct(product, profile),
        profile=ProfileNotificationFlags(
            notifications_enabled=bool(profile.get("notifications_enabled", True)),
            default_threshold_pct=int(profile.get("default_threshold_pct", 20)),
            revisit_prompts_enabled=bool(profile.get("revisit_prompts_enabled", True)),
            revisit_on_sale_enabled=bool(profile.get("revisit_on_sale_enabled", True)),
            revisit_stale_enabled=bool(profile.get("revisit_stale_enabled", True)),
            revisit_stale_days=int(profile.get("revisit_stale_days", 30)),
        ),
        product=ProductNotificationSnapshot(
            status=product["status"],
            notifications_enabled=bool(product.get("notifications_enabled", True)),
            notification_threshold_pct=product.get("notification_threshold_pct"),
            created_at=created_at,
            last_user_interaction_at=_parse_ts(product.get("last_user_interaction_at")),
        ),
        listings=listing_snapshots,
        recent_observations=load_price_observations(client, listings, today=today),
        recent_notifications=load_recent_notifications(
            client, user_id, UUID(str(product["id"])), as_of=evaluated_at
        ),
    )


def evaluate_product_notifications(
    ctx: NotificationEvaluationContext,
) -> list[NotificationProposal]:
    return list(default_composite_evaluator().evaluate(ctx))


def persist_proposals(
    client: Client, proposals: Sequence[NotificationProposal]
) -> None:
    for proposal in proposals:
        client.table("notifications").insert(
            {
                "user_id": str(proposal.user_id),
                "product_id": str(proposal.product_id) if proposal.product_id else None,
                "listing_id": str(proposal.listing_id) if proposal.listing_id else None,
                "type": proposal.type.value,
                "payload": proposal.payload,
                "is_read": False,
            }
        ).execute()


def run_post_scrape_evaluation(
    client: Client,
    *,
    user_id: UUID,
    product_id: UUID,
    evaluated_at: datetime,
    scrape_source: Literal["scheduled", "manual"],
    listings_before: dict[str, dict[str, Any]],
) -> list[NotificationProposal]:
    product_result = (
        client.table("products")
        .select("*")
        .eq("id", str(product_id))
        .eq("user_id", str(user_id))
        .maybe_single()
        .execute()
    )
    product = product_result.data if product_result else None
    if product is None:
        return []

    profile = get_or_create_profile(user_id)
    listings_result = (
        client.table("product_listings")
        .select("*")
        .eq("product_id", str(product_id))
        .execute()
    )
    listings = listings_result.data or []

    ctx = build_evaluation_context(
        client=client,
        user_id=user_id,
        product=product,
        profile=profile,
        listings=listings,
        listings_before=listings_before,
        evaluated_at=evaluated_at,
        scrape_source=scrape_source,
    )
    proposals = evaluate_product_notifications(ctx)
    persist_proposals(client, proposals)
    return proposals


def run_revisit_evaluation_for_active_products(
    client: Client,
    user_id: UUID,
    evaluated_at: datetime,
) -> list[NotificationProposal]:
    """Daily batch revisit step (T3.5 handoff): evaluate all active products.

    Reuses the full post-scrape evaluator; T3.5 step 7 may later split revisit-only
    evaluators if scheduled scrape-all already ran step 6 for the same pass.
    """
    products_result = (
        client.table("products")
        .select("id")
        .eq("user_id", str(user_id))
        .eq("status", "active")
        .execute()
    )
    all_proposals: list[NotificationProposal] = []
    for row in products_result.data or []:
        product_id = UUID(str(row["id"]))
        listings_result = (
            client.table("product_listings")
            .select("id,is_in_stock,scrape_failure_count")
            .eq("product_id", str(product_id))
            .execute()
        )
        listings_before = {
            str(listing["id"]): {
                "is_in_stock": listing.get("is_in_stock"),
                "scrape_failure_count": listing.get("scrape_failure_count"),
            }
            for listing in listings_result.data or []
        }
        proposals = run_post_scrape_evaluation(
            client,
            user_id=user_id,
            product_id=product_id,
            evaluated_at=evaluated_at,
            scrape_source="scheduled",
            listings_before=listings_before,
        )
        all_proposals.extend(proposals)
    return all_proposals
