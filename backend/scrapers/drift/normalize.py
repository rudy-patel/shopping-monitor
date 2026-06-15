"""Normalize ProductSnapshot into a stable drift fingerprint."""

from __future__ import annotations

from typing import Literal

from scrapers.benchmark.types import FieldExpect
from scrapers.contract import ProductSnapshot
from scrapers.drift.types import DriftSnapshot

_BESTBUY_EXTRACTION_ALIASES = frozenset({"jsonld", "bestbuy_api"})


def variant_count_bucket(count: int) -> Literal["0", "1", "2+"]:
    if count <= 0:
        return "0"
    if count == 1:
        return "1"
    return "2+"


def _canonical_extraction(retailer_slug: str, extraction: object | None) -> str | None:
    if extraction is None:
        return None
    value = str(extraction)
    if retailer_slug == "bestbuy_ca" and value in _BESTBUY_EXTRACTION_ALIASES:
        return "bestbuy"
    return value


def normalize(snapshot: ProductSnapshot) -> DriftSnapshot:
    attribute_names = sorted(
        {
            attribute.attribute_name
            for combination in snapshot.available_variants
            for attribute in combination.attributes
        }
    )
    selected_names = sorted(
        attribute.attribute_name for attribute in (snapshot.selected_variant or [])
    )
    extraction = _canonical_extraction(
        snapshot.retailer_slug,
        snapshot.raw_snapshot.get("extraction"),
    )
    return DriftSnapshot(
        has_title=bool(snapshot.title.strip()) if snapshot.title else False,
        has_price=snapshot.current_price_cents >= 0,
        has_stock=True,
        has_image=snapshot.image_url is not None,
        has_variants=len(snapshot.available_variants) > 0,
        variant_attribute_names=attribute_names,
        variant_count_bucket=variant_count_bucket(len(snapshot.available_variants)),
        selected_variant_attribute_names=selected_names,
        extraction=extraction,
    )


def check_expect_fields(snapshot: ProductSnapshot, expect: FieldExpect) -> list[str]:
    normalized = normalize(snapshot)
    failures: list[str] = []
    if expect.title and not normalized.has_title:
        failures.append("title")
    if expect.price and not normalized.has_price:
        failures.append("price")
    if expect.stock and not normalized.has_stock:
        failures.append("stock")
    if expect.image and not normalized.has_image:
        failures.append("image")
    if expect.variants and not normalized.has_variants:
        failures.append("variants")
    return failures
