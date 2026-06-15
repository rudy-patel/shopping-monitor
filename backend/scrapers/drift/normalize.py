"""Normalize ProductSnapshot into a stable drift fingerprint."""

from __future__ import annotations

from typing import Literal

from scrapers.benchmark.types import FieldExpect
from scrapers.contract import ProductSnapshot
from scrapers.drift.types import DriftSnapshot


def variant_count_bucket(count: int) -> Literal["0", "1", "2+"]:
    if count <= 0:
        return "0"
    if count == 1:
        return "1"
    return "2+"


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
    raw = snapshot.raw_snapshot
    schema_types_raw = raw.get("schema_types")
    schema_types = (
        sorted(str(item) for item in schema_types_raw)
        if isinstance(schema_types_raw, list)
        else None
    )
    extraction = raw.get("extraction")
    return DriftSnapshot(
        has_title=bool(snapshot.title.strip()) if snapshot.title else False,
        has_price=snapshot.current_price_cents >= 0,
        has_stock=True,
        has_image=snapshot.image_url is not None,
        has_variants=len(snapshot.available_variants) > 0,
        variant_attribute_names=attribute_names,
        variant_count_bucket=variant_count_bucket(len(snapshot.available_variants)),
        selected_variant_attribute_names=selected_names,
        source=snapshot.source.value,
        extraction=str(extraction) if extraction is not None else None,
        schema_types=schema_types,
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
