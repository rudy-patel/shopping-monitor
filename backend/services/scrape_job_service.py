"""Scheduled scrape-all job orchestration (T3.5)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from supabase import Client

from core.logging import get_logger
from scrapers.exceptions import NotCanadianListingError
from services.notification_evaluation import (
    run_post_scrape_evaluation,
    run_revisit_evaluation_for_active_products,
)
from services.product_service import (
    ScrapeOutcome,
    persist_listing_scrape_result,
    scrape_listing_url,
)

logger = get_logger(__name__)

SCRAPE_ALL_ADVISORY_LOCK_KEY = 8675309
SUCCESS_RATE_WARNING_THRESHOLD = 0.80


@dataclass(frozen=True)
class ScrapeAllResult:
    status: Literal["completed", "skipped"]
    reason: str | None
    listings_total: int
    listings_ok: int
    listings_failed: int
    success_rate: float
    products_evaluated: int
    users_revisit_evaluated: int
    notifications_created: int
    duration_seconds: float


def try_acquire_scrape_all_lock(client: Client) -> bool:
    result = client.rpc("try_acquire_scrape_all_lock").execute()
    return bool(result.data)


def release_scrape_all_lock(client: Client) -> bool:
    result = client.rpc("release_scrape_all_lock").execute()
    return bool(result.data)


def _is_retryable_outcome(outcome: ScrapeOutcome) -> bool:
    if outcome.scrape_status == "ok":
        return False
    if outcome.scrape_status == "blocked":
        return False
    return True


def scrape_listing_with_retry(
    *,
    retailer_slug: str,
    url: str,
    max_retries: int = 2,
) -> ScrapeOutcome:
    last_outcome: ScrapeOutcome | None = None
    for attempt in range(max_retries + 1):
        try:
            outcome = scrape_listing_url(retailer_slug=retailer_slug, url=url)
        except NotCanadianListingError:
            raise
        last_outcome = outcome
        if not _is_retryable_outcome(outcome):
            return outcome
        if attempt < max_retries:
            time.sleep(2**attempt)
    assert last_outcome is not None
    return last_outcome


def load_listings_for_scheduled_scrape(client: Client) -> list[dict[str, Any]]:
    products_result = (
        client.table("products")
        .select("id,user_id")
        .in_("status", ["active", "needs_input"])
        .execute()
    )
    products = products_result.data or []
    if not products:
        return []

    product_user_map = {
        str(row["id"]): str(row["user_id"]) for row in products
    }
    product_ids = list(product_user_map.keys())

    listings_result = (
        client.table("product_listings")
        .select("*")
        .in_("product_id", product_ids)
        .execute()
    )
    listings: list[dict[str, Any]] = []
    for row in listings_result.data or []:
        listing = dict(row)
        listing["user_id"] = product_user_map[str(row["product_id"])]
        listings.append(listing)
    return listings


def _load_listings_before_for_product(
    client: Client, product_id: str
) -> dict[str, dict[str, Any]]:
    listings_result = (
        client.table("product_listings")
        .select("id,is_in_stock,scrape_failure_count")
        .eq("product_id", product_id)
        .execute()
    )
    return {
        str(listing["id"]): {
            "is_in_stock": listing.get("is_in_stock"),
            "scrape_failure_count": int(listing.get("scrape_failure_count") or 0),
        }
        for listing in listings_result.data or []
    }


def distinct_users_with_active_products(client: Client) -> list[UUID]:
    result = (
        client.table("products")
        .select("user_id")
        .eq("status", "active")
        .execute()
    )
    seen: set[str] = set()
    user_ids: list[UUID] = []
    for row in result.data or []:
        user_id = str(row["user_id"])
        if user_id in seen:
            continue
        seen.add(user_id)
        user_ids.append(UUID(user_id))
    return user_ids


def run_scrape_all(
    client: Client, *, evaluated_at: datetime | None = None
) -> ScrapeAllResult:
    started_at = datetime.now(UTC)
    evaluated_at = evaluated_at or started_at

    if not try_acquire_scrape_all_lock(client):
        logger.info(
            "scrape_all_skipped",
            extra={"reason": "lock_not_acquired"},
        )
        return ScrapeAllResult(
            status="skipped",
            reason="lock_not_acquired",
            listings_total=0,
            listings_ok=0,
            listings_failed=0,
            success_rate=0.0,
            products_evaluated=0,
            users_revisit_evaluated=0,
            notifications_created=0,
            duration_seconds=0.0,
        )

    listings_total = 0
    listings_ok = 0
    listings_failed = 0

    try:
        listings = load_listings_for_scheduled_scrape(client)
        listings_total = len(listings)
        touched_products: dict[tuple[UUID, UUID], dict[str, dict[str, Any]]] = {}

        logger.info("scrape_all_started", extra={"listings_total": listings_total})

        for listing in listings:
            user_id = UUID(str(listing["user_id"]))
            product_id = UUID(str(listing["product_id"]))
            key = (user_id, product_id)
            if key not in touched_products:
                touched_products[key] = _load_listings_before_for_product(
                    client, str(product_id)
                )

            outcome = scrape_listing_with_retry(
                retailer_slug=listing["retailer_slug"],
                url=listing["url"],
            )
            persist_listing_scrape_result(
                client, listing, outcome, source="scheduled"
            )

            if outcome.scrape_status == "ok":
                listings_ok += 1
            else:
                listings_failed += 1

        all_proposals = []
        for (user_id, product_id), listings_before in touched_products.items():
            proposals = run_post_scrape_evaluation(
                client,
                user_id=user_id,
                product_id=product_id,
                evaluated_at=evaluated_at,
                scrape_source="scheduled",
                listings_before=listings_before,
                mode="scrape_triggered",
            )
            all_proposals.extend(proposals)
        products_evaluated = len(touched_products)

        user_ids = distinct_users_with_active_products(client)
        users_revisit_evaluated = len(user_ids)
        for user_id in user_ids:
            all_proposals.extend(
                run_revisit_evaluation_for_active_products(
                    client,
                    user_id,
                    evaluated_at,
                )
            )

        notifications_created = len(all_proposals)
        success_rate = listings_ok / listings_total if listings_total else 1.0
        duration_seconds = (datetime.now(UTC) - started_at).total_seconds()

        if listings_total and success_rate < SUCCESS_RATE_WARNING_THRESHOLD:
            logger.warning(
                "scrape_all_low_success_rate",
                extra={
                    "listings_total": listings_total,
                    "listings_ok": listings_ok,
                    "listings_failed": listings_failed,
                    "success_rate": success_rate,
                },
            )

        logger.info(
            "scrape_all_completed",
            extra={
                "listings_total": listings_total,
                "listings_ok": listings_ok,
                "listings_failed": listings_failed,
                "success_rate": success_rate,
                "products_evaluated": products_evaluated,
                "users_revisit_evaluated": users_revisit_evaluated,
                "notifications_created": notifications_created,
                "duration_seconds": duration_seconds,
            },
        )

        return ScrapeAllResult(
            status="completed",
            reason=None,
            listings_total=listings_total,
            listings_ok=listings_ok,
            listings_failed=listings_failed,
            success_rate=round(success_rate, 3),
            products_evaluated=products_evaluated,
            users_revisit_evaluated=users_revisit_evaluated,
            notifications_created=notifications_created,
            duration_seconds=round(duration_seconds, 1),
        )
    finally:
        release_scrape_all_lock(client)
