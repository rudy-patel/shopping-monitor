"""Seed production demo catalog for a signed-in user (service-role writes).

NOT run in CI. Uses manifest file for idempotent cleanup without title prefixes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

from scripts.demo_seed_helpers import (  # noqa: E402
    DEFAULT_DEMO_SCRAPE_DAYS_AGO,
    build_price_history_rows,
    history_days_for_product,
    listing_is_primary,
    load_catalog,
    resolve_demo_seed_scope,
    scrape_snapshot,
)

load_dotenv(_BACKEND_DIR / ".env")

MANIFEST_PATH = Path(__file__).with_name(".demo_seed_manifest.json")


def _refuse_prod_writes_in_ci() -> None:
    if os.environ.get("CI"):
        raise RuntimeError("Refusing production demo writes in CI.")


def _service_client():
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key or "your-project" in url or "your-" in key:
        raise RuntimeError(
            "Missing real SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY in backend/.env"
        )
    return create_client(url, key)


def _resolve_user_id(admin, email: str) -> str:
    target = email.strip().lower()
    for user in admin.auth.admin.list_users(per_page=200):
        user_email = getattr(user, "email", None)
        if user_email and user_email.strip().lower() == target:
            return str(user.id)
    raise RuntimeError(
        f"No auth user for {email!r}. Sign in on production once, then re-run."
    )


def _ensure_profile(admin, user_id: str) -> None:
    row = admin.table("profiles").select("user_id").eq("user_id", user_id).execute()
    if row.data:
        return
    admin.table("profiles").insert({"user_id": user_id}).execute()


def _load_manifest() -> dict[str, Any] | None:
    if not MANIFEST_PATH.exists():
        return None
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _save_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _iso_at(days_ago: int, *, hour: int = 12) -> str:
    dt = datetime.now(UTC).replace(hour=hour, minute=0, second=0, microsecond=0)
    dt -= timedelta(days=days_ago)
    return dt.isoformat()


def _seed_product(
    admin,
    *,
    user_id: str,
    spec: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    product_id = str(uuid4())
    listing_ids: list[str] = []
    trend = spec["trend"]
    status = spec["status"]
    created_days_ago = int(spec.get("created_days_ago", 14))
    created_at = _iso_at(created_days_ago)
    archived_days_ago = int(spec.get("archived_days_ago", 0)) if status == "archived" else 0
    updated_at = _iso_at(archived_days_ago) if archived_days_ago else created_at
    last_interaction_days = spec.get("last_user_interaction_days_ago")
    last_user_interaction_at = (
        _iso_at(int(last_interaction_days)) if last_interaction_days is not None else None
    )

    listing_specs = spec["listings"]
    listing_count = len(listing_specs)
    end_date = date.today()
    history_days = history_days_for_product(
        status=status,
        created_days_ago=created_days_ago,
        archived_days_ago=archived_days_ago,
    )
    history_end = (
        end_date
        if status == "active"
        else end_date - timedelta(days=archived_days_ago or 0)
    )

    if dry_run:
        return {
            "product_id": product_id,
            "listing_ids": [str(uuid4()) for _ in listing_specs],
            "key": spec["key"],
            "history_rows": history_days * listing_count,
        }

    product_row = {
        "id": product_id,
        "user_id": user_id,
        "title": spec["title"],
        "brand": spec.get("brand"),
        "image_url": None,
        "category": spec["category"],
        "category_source": "llm",
        "status": status,
        "notification_threshold_pct": None,
        "notifications_enabled": True,
        "discovery_status": "complete",
        "last_refresh_at": _iso_at(DEFAULT_DEMO_SCRAPE_DAYS_AGO),
        "last_user_interaction_at": last_user_interaction_at,
        "dashboard_sort_order": spec.get("dashboard_sort_order"),
        "created_at": created_at,
        "updated_at": updated_at,
    }
    admin.table("products").insert(product_row).execute()

    for listing_spec in listing_specs:
        listing_id = str(uuid4())
        listing_ids.append(listing_id)
        price_cents = int(listing_spec["price_cents"])
        scraped_at = _iso_at(DEFAULT_DEMO_SCRAPE_DAYS_AGO)
        listing_row = {
            "id": listing_id,
            "product_id": product_id,
            "retailer_slug": listing_spec["retailer_slug"],
            "url": listing_spec["url"],
            "variant_attributes": {},
            "available_variants": listing_spec.get("available_variants"),
            "scrape_snapshot": scrape_snapshot(
                title=spec["title"],
                brand=spec.get("brand"),
                price_cents=price_cents,
            ),
            "is_primary": listing_is_primary(listing_spec, listing_count=listing_count),
            "match_confidence": listing_spec.get("match_confidence"),
            "review_status": listing_spec["review_status"],
            "last_known_price_cents": price_cents,
            "is_in_stock": True,
            "last_scraped_at": scraped_at,
            "scrape_status": "ok",
            "scrape_failure_count": 0,
            "created_at": created_at,
            "updated_at": scraped_at,
        }
        admin.table("product_listings").insert(listing_row).execute()

        history_rows = build_price_history_rows(
            listing_id=listing_id,
            current_cents=price_cents,
            trend=trend,
            days=history_days,
            end_date=history_end,
        )
        admin.table("price_history").insert(history_rows).execute()

    return {"product_id": product_id, "listing_ids": listing_ids, "key": spec["key"]}


def _seed_notifications(
    admin,
    *,
    user_id: str,
    catalog: dict[str, Any],
    product_map: dict[str, dict[str, Any]],
    dry_run: bool,
) -> list[str]:
    notification_ids: list[str] = []
    digest_guard = datetime.now(UTC).isoformat()

    for note in catalog.get("notifications", []):
        notification_id = str(uuid4())
        product_key = note["product_key"]
        product_entry = product_map[product_key]

        listing_id = None
        listing_index = note.get("listing_index")
        if listing_index is not None:
            listing_id = product_entry["listing_ids"][int(listing_index)]

        row = {
            "id": notification_id,
            "user_id": user_id,
            "product_id": product_entry["product_id"],
            "listing_id": listing_id,
            "type": note["type"],
            "payload": note.get("payload", {}),
            "is_read": bool(note.get("is_read", False)),
            "email_sent_at": digest_guard,
            "created_at": _iso_at(int(note.get("days_ago", 1))),
        }
        notification_ids.append(notification_id)
        if not dry_run:
            admin.table("notifications").insert(row).execute()

    return notification_ids


def _apply_seed(*, email: str, dry_run: bool, catalog_path: Path | None = None) -> dict[str, Any]:
    catalog = load_catalog(catalog_path)

    admin = _service_client()
    user_id = _resolve_user_id(admin, email)
    _ensure_profile(admin, user_id)

    existing = _load_manifest()
    if existing and existing.get("user_id") == user_id and not dry_run:
        raise RuntimeError(
            f"Manifest already exists for {email}. Run --cleanup first or --force."
        )

    product_map: dict[str, dict[str, Any]] = {}
    product_ids: list[str] = []
    listing_ids: list[str] = []
    summary: list[str] = []

    for spec in catalog["products"]:
        result = _seed_product(admin, user_id=user_id, spec=spec, dry_run=dry_run)
        product_map[spec["key"]] = result
        product_ids.append(result["product_id"])
        listing_ids.extend(result["listing_ids"])
        summary.append(f"{spec['status']:12} {spec['category']:8} {spec['title']}")

    notification_ids = _seed_notifications(
        admin,
        user_id=user_id,
        catalog=catalog,
        product_map=product_map,
        dry_run=dry_run,
    )

    manifest = {
        "email": email,
        "user_id": user_id,
        "seeded_at": datetime.now(UTC).isoformat(),
        "product_ids": product_ids,
        "listing_ids": listing_ids,
        "notification_ids": notification_ids,
    }

    if not dry_run:
        _save_manifest(manifest)

    return {"manifest": manifest, "summary": summary, "user_id": user_id}


def _refresh_timestamps(
    *,
    email: str,
    dry_run: bool,
    days_ago: int = DEFAULT_DEMO_SCRAPE_DAYS_AGO,
) -> dict[str, Any]:
    catalog = load_catalog()
    admin = _service_client()
    user_id = _resolve_user_id(admin, email)
    manifest = _load_manifest()

    user_products = (
        admin.table("products")
        .select("id,title")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    product_ids, manifest_listing_ids = resolve_demo_seed_scope(
        manifest=manifest,
        email=email,
        user_products=user_products,
        catalog=catalog,
    )
    if not product_ids:
        raise RuntimeError(
            f"No demo seed products found for {email!r}. "
            "Run --apply first or ensure catalog titles match existing products."
        )

    product_id_set = set(product_ids)
    if manifest_listing_ids is not None:
        listing_ids = [str(listing_id) for listing_id in manifest_listing_ids]
    else:
        rows = (
            admin.table("product_listings")
            .select("id")
            .in_("product_id", product_ids)
            .execute()
            .data
            or []
        )
        listing_ids = [str(row["id"]) for row in rows]

    scraped_at = _iso_at(days_ago)
    titles_by_id = {
        row["id"]: row["title"] for row in user_products if row["id"] in product_id_set
    }

    if not dry_run:
        for product_id in product_ids:
            admin.table("products").update({"last_refresh_at": scraped_at}).eq(
                "id", product_id
            ).eq("user_id", user_id).execute()
        for listing_id in listing_ids:
            admin.table("product_listings").update(
                {"last_scraped_at": scraped_at, "updated_at": scraped_at}
            ).eq("id", listing_id).execute()

    return {
        "user_id": user_id,
        "product_ids": product_ids,
        "listing_ids": listing_ids,
        "timestamp": scraped_at,
        "titles": sorted(titles_by_id[pid] for pid in product_ids),
    }


def _cleanup(*, email: str) -> None:
    manifest = _load_manifest()
    if manifest is None:
        print("No manifest found — nothing to clean up.")
        return
    if manifest.get("email", "").lower() != email.strip().lower():
        raise RuntimeError(
            f"Manifest email {manifest.get('email')!r} does not match {email!r}"
        )

    admin = _service_client()
    user_id = manifest["user_id"]
    deleted = 0
    for product_id in manifest.get("product_ids", []):
        admin.table("products").delete().eq("id", product_id).eq("user_id", user_id).execute()
        deleted += 1

    MANIFEST_PATH.unlink(missing_ok=True)
    print(f"Deleted {deleted} seeded products for {email} (cascaded listings/history/notifications).")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Target user email (must exist in auth)")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without writing")
    parser.add_argument("--apply", action="store_true", help="Insert demo data")
    parser.add_argument("--cleanup", action="store_true", help="Remove data from manifest")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Cleanup existing manifest then apply",
    )
    parser.add_argument(
        "--refresh-timestamps",
        action="store_true",
        help="Update last_refresh_at / last_scraped_at for seeded demo products only",
    )
    parser.add_argument(
        "--days-ago",
        type=int,
        default=DEFAULT_DEMO_SCRAPE_DAYS_AGO,
        help="Days ago for refresh timestamps (default: 1)",
    )
    args = parser.parse_args()

    if args.cleanup:
        _cleanup(email=args.email)
        return 0

    if args.refresh_timestamps:
        if args.days_ago < 0:
            parser.error("--days-ago must be >= 0")
        if not args.dry_run:
            _refuse_prod_writes_in_ci()
        result = _refresh_timestamps(
            email=args.email,
            dry_run=args.dry_run,
            days_ago=args.days_ago,
        )
        mode = "DRY RUN" if args.dry_run else "APPLIED"
        print(
            f"[{mode}] Refreshed demo timestamps for {args.email} "
            f"(user_id={result['user_id']}, at={result['timestamp']})"
        )
        for title in result["titles"]:
            print(f"  - {title}")
        print(f"  products={len(result['product_ids'])} listings={len(result['listing_ids'])}")
        if args.dry_run:
            print("Re-run with --refresh-timestamps (no --dry-run) to write to Supabase.")
        return 0

    if args.force:
        if MANIFEST_PATH.exists():
            _cleanup(email=args.email)

    if not args.dry_run and not args.apply:
        parser.error("Specify --dry-run or --apply (or --cleanup / --refresh-timestamps)")

    if args.apply:
        _refuse_prod_writes_in_ci()

    result = _apply_seed(email=args.email, dry_run=args.dry_run)
    mode = "DRY RUN" if args.dry_run else "APPLIED"
    print(f"[{mode}] Seeded catalog for {args.email} (user_id={result['user_id']})")
    for line in result["summary"]:
        print(f"  - {line}")
    print(
        f"  products={len(result['manifest']['product_ids'])} "
        f"notifications={len(result['manifest']['notification_ids'])}"
    )
    if args.dry_run:
        print("Re-run with --apply to write to Supabase.")
    else:
        print(f"Manifest: {MANIFEST_PATH}")
        print("Open https://shopping-monitor-nine.vercel.app and sign in with Google.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
