"""Cross-retailer discovery orchestrator (PRD §7.3, T3.1; seed path T8.4)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from core.logging import get_logger
from db.supabase_client import get_service_role_client, response_first_row
from scrapers.exceptions import RetailerNotSupportedError
from scrapers.registry import lookup_by_url
from services.factory import get_llm_provider
from services.llm import LlmDiscoveryCandidate, LlmDiscoveryResult
from services.matching import classify_match, compute_match_confidence
from services.product_service import (
    _build_scrape_snapshot,
    count_cap_listings,
    scrape_listing_url,
    variant_attrs_to_dict,
)

logger = get_logger(__name__)

MAX_NON_PRIMARY_AUTO_ADDED = 4
MAX_TOTAL_LISTINGS = 5
MAX_LLM_CANDIDATES = 8


def _truncate_justification(text: str, *, max_len: int = 60) -> str:
    """Tight one-liner for review queue; no score breakdown."""
    stripped = " ".join(text.split())
    if len(stripped) <= max_len:
        return stripped
    return stripped[: max_len - 1].rstrip() + "…"


def _normalize_url(url: str) -> str:
    return url.strip().lower().rstrip("/")


def _load_product_context(client: Any, product_id: UUID) -> dict[str, Any] | None:
    result = (
        client.table("products")
        .select("*")
        .eq("id", str(product_id))
        .maybe_single()
        .execute()
    )
    if result is None:
        return None
    return response_first_row(result)


def _load_listings(client: Any, product_id: str) -> list[dict[str, Any]]:
    result = (
        client.table("product_listings")
        .select("*")
        .eq("product_id", product_id)
        .execute()
    )
    return result.data or []


def _set_discovery_status(client: Any, product_id: UUID, status: str) -> None:
    client.table("products").update({"discovery_status": status}).eq(
        "id", str(product_id)
    ).execute()


def _count_non_primary_auto_added(listings: list[dict[str, Any]]) -> int:
    return sum(
        1
        for row in listings
        if not row.get("is_primary") and row.get("review_status") == "auto_added"
    )


def _existing_retailer_slugs(listings: list[dict[str, Any]]) -> set[str]:
    return {row["retailer_slug"] for row in listings}


def _existing_normalized_urls(listings: list[dict[str, Any]]) -> set[str]:
    return {_normalize_url(row["url"]) for row in listings}


def _insert_discovered_listing(
    client: Any,
    *,
    product_id: str,
    retailer_slug: str,
    url: str,
    snapshot: Any,
    scrape_status: str,
    price_cents: int | None,
    review_status: str,
    match_confidence: float,
    justification: str,
) -> dict[str, Any]:
    snapshot_payload = _build_scrape_snapshot(snapshot)
    snapshot_payload["discovery_justification"] = _truncate_justification(justification)
    row = (
        client.table("product_listings")
        .insert(
            {
                "product_id": product_id,
                "retailer_slug": retailer_slug,
                "url": url,
                "variant_attributes": variant_attrs_to_dict(snapshot.selected_variant),
                "available_variants": None,
                "scrape_snapshot": snapshot_payload,
                "is_primary": False,
                "review_status": review_status,
                "match_confidence": match_confidence,
                "last_known_price_cents": price_cents,
                "is_in_stock": snapshot.is_in_stock,
                "last_scraped_at": snapshot.scraped_at.isoformat(),
                "scrape_status": scrape_status,
            }
        )
        .select("*")
        .execute()
    )
    listing = response_first_row(row)
    if listing is None:
        raise RuntimeError("Listing insert returned no row")

    if price_cents is not None:
        client.table("price_history").insert(
            {
                "listing_id": listing["id"],
                "price_cents": price_cents,
                "is_in_stock": snapshot.is_in_stock,
                "source": "scheduled",
            }
        ).execute()

    return listing


def _seed_to_candidates(
    seed: Sequence[tuple[str, str]],
) -> list[LlmDiscoveryCandidate]:
    """Convert search-flow seed (retailer_slug, url) pairs into discovery candidates."""
    candidates: list[LlmDiscoveryCandidate] = []
    for _retailer_slug, url in seed:
        try:
            candidates.append(
                LlmDiscoveryCandidate(url=url, justification="Found via search")
            )
        except Exception:
            continue
    return candidates


def run_discovery_for_product(
    product_id: UUID,
    *,
    seed: Sequence[tuple[str, str]] | None = None,
) -> None:
    """Background job: discover cross-retailer listings for one product.

    When ``seed`` is provided (search-based add, T8.4) the LLM ``discover()`` call is
    skipped and the seed URLs are used directly as candidates. The same scoring,
    auto-add, needs-review, and cap pipeline runs regardless of source.
    """
    client = get_service_role_client()

    try:
        product = _load_product_context(client, product_id)
        if product is None:
            logger.warning(
                "discovery_product_missing",
                extra={"product_id": str(product_id)},
            )
            return

        listings = _load_listings(client, str(product_id))
        primary = next((row for row in listings if row.get("is_primary")), None)
        if primary is None:
            logger.warning(
                "discovery_primary_missing",
                extra={"product_id": str(product_id)},
            )
            _set_discovery_status(client, product_id, "complete")
            return

        # Generic primary listings (link-only or best-effort) don't produce reliable
        # reference snapshots, so we skip cross-retailer discovery entirely.
        if primary["retailer_slug"] == "generic":
            logger.info(
                "discovery_skip_generic_primary",
                extra={"product_id": str(product_id)},
            )
            _set_discovery_status(client, product_id, "complete")
            return

        _set_discovery_status(client, product_id, "running")
        logger.info(
            "discovery_started",
            extra={
                "product_id": str(product_id),
                "listing_count": len(listings),
                "source": "seed" if seed else "llm",
            },
        )

        reference_title = product["title"]
        reference_brand = product.get("brand")
        reference_variants = primary.get("variant_attributes") or {}
        primary_retailer = primary["retailer_slug"]
        image_url = product.get("image_url")
        reference_price_cents = primary.get("last_known_price_cents")

        if seed:
            discover_result = LlmDiscoveryResult(
                candidates=_seed_to_candidates(seed)
            )
            logger.info(
                "discovery_using_seed",
                extra={
                    "product_id": str(product_id),
                    "seed_count": len(discover_result.candidates),
                },
            )
        else:
            llm = get_llm_provider()
            try:
                discover_result = llm.discover(
                    title=reference_title,
                    brand=reference_brand,
                    retailer_slug=primary_retailer,
                    variant_attributes=reference_variants,
                    image_url=image_url,
                    reference_price_cents=reference_price_cents,
                )
            except Exception as exc:
                logger.warning(
                    "discovery_llm_failed",
                    extra={"product_id": str(product_id), "error": str(exc)},
                )
                _set_discovery_status(client, product_id, "complete")
                return

        candidates = discover_result.candidates[:MAX_LLM_CANDIDATES]
        if not candidates:
            logger.info(
                "discovery_no_candidates",
                extra={"product_id": str(product_id)},
            )
            _set_discovery_status(client, product_id, "complete")
            return

        seen_retailers = _existing_retailer_slugs(listings)
        seen_urls = _existing_normalized_urls(listings)
        auto_added_count = 0
        needs_review_count = 0
        cap_count = count_cap_listings(listings)
        non_primary_auto = _count_non_primary_auto_added(listings)

        for candidate in candidates:
            if non_primary_auto >= MAX_NON_PRIMARY_AUTO_ADDED:
                logger.info(
                    "discovery_stop_auto_cap",
                    extra={"product_id": str(product_id)},
                )
                break
            if cap_count >= MAX_TOTAL_LISTINGS:
                logger.info(
                    "discovery_stop_total_cap",
                    extra={"product_id": str(product_id)},
                )
                break

            candidate_url = str(candidate.url)
            normalized = _normalize_url(candidate_url)
            if normalized in seen_urls:
                logger.info(
                    "discovery_skip_duplicate_url",
                    extra={"product_id": str(product_id), "url": candidate_url},
                )
                continue

            try:
                entry = lookup_by_url(candidate_url)
            except RetailerNotSupportedError:
                logger.info(
                    "discovery_skip_unsupported_url",
                    extra={"product_id": str(product_id), "url": candidate_url},
                )
                continue

            if entry.slug == "generic":
                logger.info(
                    "discovery_skip_generic",
                    extra={"product_id": str(product_id), "url": candidate_url},
                )
                continue

            if entry.slug in seen_retailers:
                logger.info(
                    "discovery_skip_duplicate_retailer",
                    extra={
                        "product_id": str(product_id),
                        "retailer_slug": entry.slug,
                    },
                )
                continue

            outcome = scrape_listing_url(retailer_slug=entry.slug, url=candidate_url)
            if outcome.scrape_status != "ok":
                logger.info(
                    "discovery_skip_scrape_failure",
                    extra={
                        "product_id": str(product_id),
                        "url": candidate_url,
                        "scrape_status": outcome.scrape_status,
                    },
                )
                continue

            snapshot = outcome.snapshot
            if snapshot.currency_seen != "CAD":
                logger.info(
                    "discovery_skip_non_cad",
                    extra={
                        "product_id": str(product_id),
                        "url": candidate_url,
                        "currency": snapshot.currency_seen,
                    },
                )
                continue

            if outcome.price_cents is None:
                logger.info(
                    "discovery_skip_no_price",
                    extra={"product_id": str(product_id), "url": candidate_url},
                )
                continue

            candidate_variants = variant_attrs_to_dict(snapshot.selected_variant)
            score = compute_match_confidence(
                reference_title=reference_title,
                reference_brand=reference_brand,
                reference_variants=reference_variants,
                candidate_title=snapshot.title,
                candidate_brand=snapshot.brand,
                candidate_variants=candidate_variants,
            )
            classification = classify_match(score)

            if classification == "discard":
                logger.info(
                    "discovery_discard_low_score",
                    extra={
                        "product_id": str(product_id),
                        "url": candidate_url,
                        "score": score,
                    },
                )
                continue

            review_status = (
                "auto_added" if classification == "auto_add" else "needs_review"
            )

            _insert_discovered_listing(
                client,
                product_id=str(product_id),
                retailer_slug=entry.slug,
                url=candidate_url,
                snapshot=snapshot,
                scrape_status=outcome.scrape_status,
                price_cents=outcome.price_cents,
                review_status=review_status,
                match_confidence=score,
                justification=candidate.justification,
            )
            seen_retailers.add(entry.slug)
            seen_urls.add(normalized)
            cap_count += 1

            if review_status == "auto_added":
                auto_added_count += 1
                non_primary_auto += 1
            else:
                needs_review_count += 1

            if non_primary_auto >= MAX_NON_PRIMARY_AUTO_ADDED:
                logger.info(
                    "discovery_stop_auto_cap",
                    extra={"product_id": str(product_id)},
                )
                break

        if auto_added_count + needs_review_count > 0:
            client.table("notifications").insert(
                {
                    "user_id": product["user_id"],
                    "product_id": str(product_id),
                    "type": "discovery_complete",
                    "payload": {
                        "auto_added_count": auto_added_count,
                        "needs_review_count": needs_review_count,
                    },
                }
            ).execute()

        _set_discovery_status(client, product_id, "complete")
        logger.info(
            "discovery_finished",
            extra={
                "product_id": str(product_id),
                "auto_added_count": auto_added_count,
                "needs_review_count": needs_review_count,
            },
        )
    except Exception:
        logger.exception(
            "discovery_failed",
            extra={"product_id": str(product_id)},
        )
        try:
            _set_discovery_status(client, product_id, "failed")
        except Exception:
            logger.exception(
                "discovery_status_update_failed",
                extra={"product_id": str(product_id)},
            )
