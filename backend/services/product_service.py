"""Product persistence and orchestration (T2.5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException
from postgrest.exceptions import APIError
from supabase import Client

from scrapers.contract import (
    ProductSnapshot,
    ScrapeSource,
    VariantAttribute,
    VariantCombination,
    utc_now,
)
from scrapers.exceptions import (
    FixtureNotFoundError,
    NotCanadianListingError,
    RetailerNotSupportedError,
    ScrapeBlockedError,
    ScrapeParseError,
    ScraperConfigError,
)
from scrapers.fixture_url import resolve_fixture_scenario
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret
from scrapers.http import scraper_fetch
from scrapers.mode import is_fixtures_mode  # pragma: allowlist secret
from scrapers.registry import RetailerEntry, lookup_by_url
from scrapers.structured_data import extract_from_html
from services.categorizer import CategorizationContext, CategorySource
from services.factory import get_categorizer
from services.pricing import (
    ELIGIBLE_REVIEW_STATUSES,
    TrendDirection,
    TrendResult,
    compute_trend,
)
from services.pricing_data import load_price_observations
from services.notification_evaluation import run_post_scrape_evaluation
from db.supabase_client import response_first_row
from services.profile_service import get_or_create_profile

REFRESH_COOLDOWN = timedelta(hours=1)

ProductStatus = Literal["active", "needs_input", "archived"]
ProductCategory = Literal["clothing", "shoes", "home", "tech", "other"]
ScrapeStatus = Literal["ok", "blocked", "failing"]

VALID_MANUAL_CATEGORIES = frozenset({"clothing", "shoes", "home", "tech", "other"})
CAP_COUNTING_REVIEW_STATUSES = frozenset({"auto_added", "needs_review", "accepted"})


def count_cap_listings(listings: list[dict[str, Any]]) -> int:
    return sum(
        1
        for row in listings
        if row.get("review_status") in CAP_COUNTING_REVIEW_STATUSES
    )


def get_client() -> Client:
    from db.supabase_client import get_service_role_client

    return get_service_role_client()


def variant_attrs_to_dict(attrs: list[VariantAttribute] | None) -> dict[str, str]:
    return {a.attribute_name: a.attribute_value for a in (attrs or [])}


def variants_to_jsonb(variants: list[VariantCombination]) -> list[dict[str, Any]]:
    return [v.model_dump() for v in variants]


def _normalize_variant_dict(attrs: dict[str, str]) -> dict[str, str]:
    return {key.lower(): value for key, value in attrs.items()}


def _variant_dict_from_combination(variant: dict[str, Any]) -> dict[str, str]:
    attributes = variant.get("attributes") or []
    return {
        attr["attribute_name"]: attr["attribute_value"]
        for attr in attributes
        if "attribute_name" in attr and "attribute_value" in attr
    }


def _find_matching_variant(
    available_variants: list[dict[str, Any]], requested: dict[str, str]
) -> dict[str, Any] | None:
    requested_norm = _normalize_variant_dict(requested)
    matches = [
        variant
        for variant in available_variants
        if _normalize_variant_dict(_variant_dict_from_combination(variant))
        == requested_norm
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _parse_ts(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _scrape_status_from_exception(exc: Exception) -> ScrapeStatus:
    if isinstance(exc, ScrapeBlockedError):
        return "blocked"
    return "failing"


def _build_scrape_snapshot(snapshot: ProductSnapshot) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": snapshot.title,
        "brand": snapshot.brand,
        "price_cents": snapshot.current_price_cents,
        "is_in_stock": snapshot.is_in_stock,
        "breadcrumbs": snapshot.breadcrumbs,
        "raw_snapshot": snapshot.raw_snapshot,
    }
    if snapshot.image_url:
        payload["image_url"] = str(snapshot.image_url)
    return payload


def _partial_generic_snapshot(url: str) -> ProductSnapshot:
    if is_fixtures_mode():  # pragma: allowlist secret
        scenario = resolve_fixture_scenario(url, "generic")
        html = FixtureLoader().load_text("generic", scenario)
        source = "fixture"
    else:
        response = scraper_fetch(url, retailer_slug="generic")
        html = response.body_text
        source = "structured_data"

    extracted = extract_from_html(html)
    title = extracted.title or "Unknown product"

    return ProductSnapshot(
        retailer_slug="generic",
        url=url,
        title=title,
        brand=extracted.brand,
        image_url=extracted.image_url,
        current_price_cents=0,
        currency_seen=extracted.currency or "CAD",
        is_in_stock=extracted.is_in_stock if extracted.is_in_stock is not None else True,
        available_variants=extracted.available_variants,
        selected_variant=extracted.selected_variant,
        breadcrumbs=extracted.breadcrumbs,
        scraped_at=utc_now(),
        source=ScrapeSource(source),
        raw_snapshot=extracted.raw_snapshot,
    )


@dataclass(frozen=True)
class ScrapeOutcome:
    entry: RetailerEntry
    snapshot: ProductSnapshot
    scrape_status: ScrapeStatus
    price_cents: int | None


def scrape_for_add(url: str) -> ScrapeOutcome:
    entry = lookup_by_url(url)
    try:
        snapshot = entry.scrape(url)
        return ScrapeOutcome(
            entry=entry,
            snapshot=snapshot,
            scrape_status="ok",
            price_cents=snapshot.current_price_cents,
        )
    except ScrapeBlockedError:
        if entry.slug == "generic":
            snapshot = _partial_generic_snapshot(url)
            return ScrapeOutcome(
                entry=entry,
                snapshot=snapshot,
                scrape_status="blocked",
                price_cents=None,
            )
        raise
    except (
        NotCanadianListingError,
        ScrapeParseError,
        FixtureNotFoundError,
        RetailerNotSupportedError,
        ScraperConfigError,
    ):
        raise


def scrape_listing_url(*, retailer_slug: str, url: str) -> ScrapeOutcome:
    from scrapers.registry import get

    try:
        entry = lookup_by_url(url)
    except RetailerNotSupportedError:
        entry = get(retailer_slug)

    try:
        snapshot = entry.scrape(url)
        return ScrapeOutcome(
            entry=entry,
            snapshot=snapshot,
            scrape_status="ok",
            price_cents=snapshot.current_price_cents,
        )
    except ScrapeBlockedError:
        if entry.slug == "generic":
            snapshot = _partial_generic_snapshot(url)
            return ScrapeOutcome(
                entry=entry,
                snapshot=snapshot,
                scrape_status="blocked",
                price_cents=None,
            )
        return ScrapeOutcome(
            entry=entry,
            snapshot=_empty_snapshot(entry, url),
            scrape_status="blocked",
            price_cents=None,
        )
    except Exception as exc:
        return ScrapeOutcome(
            entry=entry,
            snapshot=_empty_snapshot(entry, url),
            scrape_status=_scrape_status_from_exception(exc),
            price_cents=None,
        )


def _empty_snapshot(entry: RetailerEntry, url: str) -> ProductSnapshot:
    return ProductSnapshot(
        retailer_slug=entry.slug,
        url=url,
        title="Unknown product",
        current_price_cents=0,
        currency_seen="CAD",
        is_in_stock=False,
        scraped_at=utc_now(),
        source=ScrapeSource.FIXTURE,
    )


def _derive_product_status(snapshot: ProductSnapshot) -> ProductStatus:
    if snapshot.selected_variant is not None or len(snapshot.available_variants) <= 1:
        return "active"
    return "needs_input"


def _resolve_category(
    *,
    snapshot: ProductSnapshot,
    entry: RetailerEntry,
    category_input: str | None,
) -> tuple[ProductCategory, CategorySource]:
    manual_override: ProductCategory | None = None
    if category_input is not None:
        if category_input not in VALID_MANUAL_CATEGORIES:
            raise HTTPException(status_code=422, detail="Invalid category")
        manual_override = category_input  # type: ignore[assignment]

    result = get_categorizer().categorize(
        CategorizationContext(
            title=snapshot.title,
            brand=snapshot.brand,
            retailer_slug=entry.slug,
            breadcrumbs=snapshot.breadcrumbs,
            manual_override=manual_override,
        )
    )
    return result.category, result.source  # type: ignore[return-value]


def _listing_eligible_for_best_price(listing: dict[str, Any]) -> bool:
    price = listing.get("last_known_price_cents")
    if price is None:
        return False
    if not listing.get("is_in_stock"):
        return False
    if listing.get("is_primary"):
        return True
    return listing.get("review_status") in ELIGIBLE_REVIEW_STATUSES


def _best_price(listings: list[dict[str, Any]]) -> tuple[int | None, str | None]:
    eligible = [row for row in listings if _listing_eligible_for_best_price(row)]
    if not eligible:
        return None, None
    best = min(eligible, key=lambda row: row["last_known_price_cents"])
    return best["last_known_price_cents"], best.get("retailer_slug")


def _load_listings(client: Client, product_id: str) -> list[dict[str, Any]]:
    result = (
        client.table("product_listings")
        .select("*")
        .eq("product_id", product_id)
        .execute()
    )
    return result.data or []


def trend_label(direction: TrendDirection) -> str:
    labels = {
        TrendDirection.DOWN: "Down in the last 30 days",
        TrendDirection.SAME: "Same in the last 30 days",
        TrendDirection.UP: "Up in the last 30 days",
    }
    return labels[direction]


def _serialize_trend(trend: TrendResult) -> dict[str, Any]:
    delta_pct: float | None = None
    if trend.delta_pct is not None:
        delta_pct = float(trend.delta_pct)
    return {
        "direction": trend.direction.value,
        "delta_pct": delta_pct,
        "days_of_data": trend.days_of_data,
        "label": trend_label(trend.direction),
    }


def _effective_threshold_pct(product: dict[str, Any], profile: dict[str, Any]) -> int:
    threshold = product.get("notification_threshold_pct")
    if threshold is not None:
        return int(threshold)
    return int(profile["default_threshold_pct"])


def _max_last_scraped(listings: list[dict[str, Any]]) -> str | None:
    timestamps = [
        ts
        for row in listings
        if (ts := row.get("last_scraped_at")) is not None
    ]
    if not timestamps:
        return None
    return max(timestamps)


def _sort_listings(listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        listings,
        key=lambda row: (
            row.get("last_known_price_cents") is None,
            row.get("last_known_price_cents") if row.get("last_known_price_cents") is not None else 0,
        ),
    )


def _review_display_fields(row: dict[str, Any]) -> dict[str, Any]:
    snap = row.get("scrape_snapshot") or {}
    return {
        "review_title": snap.get("title"),
        "review_image_url": snap.get("image_url"),
        "review_reason": snap.get("discovery_justification") or None,
    }


def _serialize_listing(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "retailer_slug": row["retailer_slug"],
        "url": row["url"],
        "variant_attributes": row.get("variant_attributes") or {},
        "available_variants": row.get("available_variants"),
        "is_primary": row.get("is_primary", False),
        "review_status": row["review_status"],
        "last_known_price_cents": row.get("last_known_price_cents"),
        "is_in_stock": row.get("is_in_stock"),
        "last_scraped_at": row.get("last_scraped_at"),
        "scrape_status": row.get("scrape_status"),
        "match_confidence": row.get("match_confidence"),
        **_review_display_fields(row),
    }


def build_product_detail(
    *,
    product: dict[str, Any],
    profile: dict[str, Any],
    listings: list[dict[str, Any]],
    today: date | None = None,
) -> dict[str, Any]:
    today = today or date.today()
    sorted_listings = _sort_listings(listings)
    best_price_cents, best_retailer_slug = _best_price(sorted_listings)
    observations = load_price_observations(
        get_client(), sorted_listings, today=today
    )
    trend = compute_trend(observations, today=today)
    needs_review_count = sum(
        1 for row in sorted_listings if row.get("review_status") == "needs_review"
    )

    return {
        "id": product["id"],
        "title": product["title"],
        "brand": product.get("brand"),
        "image_url": product.get("image_url"),
        "category": product["category"],
        "category_source": product["category_source"],
        "status": product["status"],
        "notification_threshold_pct": product.get("notification_threshold_pct"),
        "notifications_enabled": product.get("notifications_enabled", True),
        "discovery_status": product["discovery_status"],
        "last_refresh_at": product.get("last_refresh_at"),
        "last_user_interaction_at": product.get("last_user_interaction_at"),
        "created_at": product["created_at"],
        "updated_at": product["updated_at"],
        "best_price_cents": best_price_cents,
        "best_retailer_slug": best_retailer_slug,
        "trend": _serialize_trend(trend),
        "listing_count": len(sorted_listings),
        "effective_threshold_pct": _effective_threshold_pct(product, profile),
        "last_scraped_at": _max_last_scraped(sorted_listings),
        "needs_review_count": needs_review_count,
        "listings": [_serialize_listing(row) for row in sorted_listings],
    }


def _get_owned_product(client: Client, *, product_id: UUID, user_id: UUID) -> dict[str, Any]:
    result = (
        client.table("products")
        .select("*")
        .eq("id", str(product_id))
        .eq("user_id", str(user_id))
        .maybe_single()
        .execute()
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    row = response_first_row(result)
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return row


def create_product(
    *,
    user_id: UUID,
    url: str,
    category: str | None = None,
) -> dict[str, Any]:
    try:
        outcome = scrape_for_add(url)
    except NotCanadianListingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (
        ScrapeParseError,
        FixtureNotFoundError,
        RetailerNotSupportedError,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ScrapeBlockedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ScraperConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    snapshot = outcome.snapshot
    profile = get_or_create_profile(user_id)
    category_value, category_source = _resolve_category(
        snapshot=snapshot,
        entry=outcome.entry,
        category_input=category,
    )
    status = _derive_product_status(snapshot)
    client = get_client()

    product_row = (
        client.table("products")
        .insert(
            {
                "user_id": str(user_id),
                "title": snapshot.title,
                "brand": snapshot.brand,
                "image_url": str(snapshot.image_url) if snapshot.image_url else None,
                "category": category_value,
                "category_source": category_source,
                "status": status,
                "discovery_status": "pending",
                "last_refresh_at": None,
            }
        )
        .select("*")
        .execute()
    )
    product = response_first_row(product_row)
    if product is None:
        raise RuntimeError("Product insert returned no row")
    product_id = product["id"]

    listing_row = (
        client.table("product_listings")
        .insert(
            {
                "product_id": product_id,
                "retailer_slug": outcome.entry.slug,
                "url": url,
                "variant_attributes": variant_attrs_to_dict(snapshot.selected_variant),
                "available_variants": variants_to_jsonb(snapshot.available_variants),
                "scrape_snapshot": _build_scrape_snapshot(snapshot),
                "is_primary": True,
                "review_status": "accepted",
                "last_known_price_cents": outcome.price_cents,
                "is_in_stock": snapshot.is_in_stock,
                "last_scraped_at": snapshot.scraped_at.isoformat(),
                "scrape_status": outcome.scrape_status,
            }
        )
        .select("*")
        .execute()
    )
    listing = response_first_row(listing_row)
    if listing is None:
        raise RuntimeError("Listing insert returned no row")

    if outcome.price_cents is not None:
        client.table("price_history").insert(
            {
                "listing_id": listing["id"],
                "price_cents": outcome.price_cents,
                "is_in_stock": snapshot.is_in_stock,
                "source": "scheduled",
            }
        ).execute()

    if status == "needs_input":
        client.table("notifications").insert(
            {
                "user_id": str(user_id),
                "product_id": product_id,
                "type": "needs_input",
                "payload": {},
            }
        ).execute()

    listings = [listing]
    return build_product_detail(product=product, profile=profile, listings=listings)


def list_products(
    *,
    user_id: UUID,
    status: ProductStatus | None = "active",
    category: ProductCategory | None = None,
) -> list[dict[str, Any]]:
    client = get_client()
    profile = get_or_create_profile(user_id)
    query = client.table("products").select("*").eq("user_id", str(user_id))
    if status is not None:
        query = query.eq("status", status)
    if category is not None:
        query = query.eq("category", category)
    result = query.execute()
    products = result.data or []
    products.sort(key=lambda row: row.get("created_at", ""), reverse=True)

    summaries: list[dict[str, Any]] = []
    for product in products:
        listings = _load_listings(client, product["id"])
        detail = build_product_detail(product=product, profile=profile, listings=listings)
        detail.pop("listings")
        summaries.append(detail)
    return summaries


def get_product(*, user_id: UUID, product_id: UUID) -> dict[str, Any]:
    client = get_client()
    product = _get_owned_product(client, product_id=product_id, user_id=user_id)
    profile = get_or_create_profile(user_id)
    listings = _load_listings(client, product["id"])
    return build_product_detail(product=product, profile=profile, listings=listings)


def update_product(
    *,
    user_id: UUID,
    product_id: UUID,
    patch: dict[str, Any],
) -> dict[str, Any]:
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    client = get_client()
    _get_owned_product(client, product_id=product_id, user_id=user_id)
    update_payload = dict(patch)
    update_payload["last_user_interaction_at"] = datetime.now(UTC).isoformat()
    if "category" in update_payload:
        update_payload["category_source"] = "manual"

    try:
        updated = (
            client.table("products")
            .update(update_payload)
            .eq("id", str(product_id))
            .eq("user_id", str(user_id))
            .select("*")
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    product = response_first_row(updated)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    profile = get_or_create_profile(user_id)
    listings = _load_listings(client, str(product_id))
    return build_product_detail(product=product, profile=profile, listings=listings)


def delete_product(*, user_id: UUID, product_id: UUID) -> None:
    client = get_client()
    _get_owned_product(client, product_id=product_id, user_id=user_id)
    client.table("products").delete().eq("id", str(product_id)).eq(
        "user_id", str(user_id)
    ).execute()


def persist_listing_scrape_result(
    client: Client,
    listing: dict[str, Any],
    outcome: ScrapeOutcome,
    *,
    source: Literal["scheduled", "manual"],
) -> None:
    """Update listing row; insert price_history on successful price extract."""
    update_payload: dict[str, Any] = {
        "last_scraped_at": outcome.snapshot.scraped_at.isoformat(),
        "scrape_status": outcome.scrape_status,
    }
    if outcome.scrape_status == "ok" and outcome.price_cents is not None:
        update_payload["scrape_snapshot"] = _build_scrape_snapshot(outcome.snapshot)
        update_payload["last_known_price_cents"] = outcome.price_cents
        update_payload["is_in_stock"] = outcome.snapshot.is_in_stock
        update_payload["scrape_failure_count"] = 0
    elif outcome.scrape_status != "ok":
        update_payload["scrape_failure_count"] = int(
            listing.get("scrape_failure_count") or 0
        ) + 1

    client.table("product_listings").update(update_payload).eq(
        "id", listing["id"]
    ).execute()

    if outcome.scrape_status == "ok" and outcome.price_cents is not None:
        client.table("price_history").insert(
            {
                "listing_id": listing["id"],
                "price_cents": outcome.price_cents,
                "is_in_stock": outcome.snapshot.is_in_stock,
                "source": source,
            }
        ).execute()


def refresh_product(*, user_id: UUID, product_id: UUID) -> dict[str, Any]:
    client = get_client()
    product = _get_owned_product(client, product_id=product_id, user_id=user_id)
    last_refresh = _parse_ts(product.get("last_refresh_at"))
    if last_refresh is not None and datetime.now(UTC) - last_refresh < REFRESH_COOLDOWN:
        raise HTTPException(status_code=429, detail="Refresh cooldown active")

    listings = _load_listings(client, product["id"])
    now_dt = datetime.now(UTC)
    now = now_dt.isoformat()
    listings_before = {
        str(listing["id"]): {
            "is_in_stock": listing.get("is_in_stock"),
            "scrape_failure_count": int(listing.get("scrape_failure_count") or 0),
        }
        for listing in listings
    }

    for listing in listings:
        outcome = scrape_listing_url(
            retailer_slug=listing["retailer_slug"],
            url=listing["url"],
        )
        persist_listing_scrape_result(
            client, listing, outcome, source="manual"
        )

    run_post_scrape_evaluation(
        client,
        user_id=user_id,
        product_id=product_id,
        evaluated_at=now_dt,
        scrape_source="manual",
        listings_before=listings_before,
    )

    client.table("products").update(
        {
            "last_refresh_at": now,
            "last_user_interaction_at": now,
        }
    ).eq("id", product["id"]).execute()

    updated_product = _get_owned_product(client, product_id=product_id, user_id=user_id)
    profile = get_or_create_profile(user_id)
    refreshed_listings = _load_listings(client, product["id"])
    return build_product_detail(
        product=updated_product, profile=profile, listings=refreshed_listings
    )


def _touch_user_interaction(client: Client, product_id: UUID) -> None:
    client.table("products").update(
        {"last_user_interaction_at": datetime.now(UTC).isoformat()}
    ).eq("id", str(product_id)).execute()


def _get_owned_listing(
    client: Client,
    *,
    user_id: UUID,
    product_id: UUID,
    listing_id: UUID,
) -> dict[str, Any]:
    _get_owned_product(client, product_id=product_id, user_id=user_id)
    result = (
        client.table("product_listings")
        .select("*")
        .eq("id", str(listing_id))
        .eq("product_id", str(product_id))
        .maybe_single()
        .execute()
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    row = response_first_row(result)
    if row is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return row


def _detail_after_listing_change(
    client: Client, *, user_id: UUID, product_id: UUID
) -> dict[str, Any]:
    product = _get_owned_product(client, product_id=product_id, user_id=user_id)
    profile = get_or_create_profile(user_id)
    listings = _load_listings(client, str(product_id))
    return build_product_detail(product=product, profile=profile, listings=listings)


def accept_listing(
    *,
    user_id: UUID,
    product_id: UUID,
    listing_id: UUID,
) -> dict[str, Any]:
    client = get_client()
    listing = _get_owned_listing(
        client, user_id=user_id, product_id=product_id, listing_id=listing_id
    )
    if listing.get("review_status") != "needs_review":
        raise HTTPException(status_code=409, detail="Listing is not pending review")

    client.table("product_listings").update({"review_status": "accepted"}).eq(
        "id", str(listing_id)
    ).execute()
    _touch_user_interaction(client, product_id)
    return _detail_after_listing_change(client, user_id=user_id, product_id=product_id)


def reject_listing(
    *,
    user_id: UUID,
    product_id: UUID,
    listing_id: UUID,
) -> dict[str, Any]:
    client = get_client()
    listing = _get_owned_listing(
        client, user_id=user_id, product_id=product_id, listing_id=listing_id
    )
    if listing.get("review_status") != "needs_review":
        raise HTTPException(status_code=409, detail="Listing is not pending review")

    client.table("product_listings").update({"review_status": "rejected"}).eq(
        "id", str(listing_id)
    ).execute()
    _touch_user_interaction(client, product_id)
    return _detail_after_listing_change(client, user_id=user_id, product_id=product_id)


def delete_listing(
    *,
    user_id: UUID,
    product_id: UUID,
    listing_id: UUID,
) -> dict[str, Any]:
    client = get_client()
    listing = _get_owned_listing(
        client, user_id=user_id, product_id=product_id, listing_id=listing_id
    )
    if listing.get("is_primary"):
        raise HTTPException(status_code=409, detail="Cannot remove primary listing")

    client.table("product_listings").delete().eq("id", str(listing_id)).execute()
    _touch_user_interaction(client, product_id)
    return _detail_after_listing_change(client, user_id=user_id, product_id=product_id)


def select_variant(
    *,
    user_id: UUID,
    product_id: UUID,
    variant_attributes: dict[str, str],
) -> dict[str, Any]:
    client = get_client()
    product = _get_owned_product(client, product_id=product_id, user_id=user_id)
    if product["status"] != "needs_input":
        raise HTTPException(
            status_code=409,
            detail="Product does not require variant selection",
        )

    listings = _load_listings(client, product["id"])
    primary = next((row for row in listings if row.get("is_primary")), None)
    if primary is None:
        raise HTTPException(status_code=422, detail="Primary listing not found")

    available = primary.get("available_variants") or []
    match = _find_matching_variant(available, variant_attributes)
    if match is None:
        raise HTTPException(status_code=422, detail="Variant attributes do not match")

    now = datetime.now(UTC).isoformat()
    client.table("product_listings").update(
        {"variant_attributes": variant_attributes}
    ).eq("id", primary["id"]).execute()
    updated = (
        client.table("products")
        .update(
            {
                "status": "active",
                "last_user_interaction_at": now,
            }
        )
        .eq("id", product["id"])
        .select("*")
        .execute()
    )
    updated_product = response_first_row(updated)
    if updated_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    profile = get_or_create_profile(user_id)
    refreshed_listings = _load_listings(client, product["id"])
    return build_product_detail(
        product=updated_product, profile=profile, listings=refreshed_listings
    )
