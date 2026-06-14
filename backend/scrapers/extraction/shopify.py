"""Shopify theme meta extraction (variants) to complement JSON-LD/OG parsing."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlsplit

from scrapers.contract import VariantAttribute, VariantCombination
from scrapers.extraction.types import ExtractedFields
from scrapers.structured_data import extract_from_html

_META_MARKER = "var meta = "


def variant_id_from_url(url: str) -> str | None:
    """Return Shopify variant id from ``?variant=`` query param when present."""
    query = parse_qs(urlsplit(url).query)
    values = query.get("variant")
    if not values:
        return None
    variant_id = values[0].strip()
    return variant_id or None


def _parse_meta_json(html: str) -> dict[str, Any] | None:
    start = html.find(_META_MARKER)
    if start < 0:
        return None
    cursor = start + len(_META_MARKER)
    if cursor >= len(html) or html[cursor] != "{":
        return None

    depth = 0
    for index in range(cursor, len(html)):
        char = html[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    payload = json.loads(html[cursor : index + 1])
                except json.JSONDecodeError:
                    return None
                product = payload.get("product")
                return product if isinstance(product, dict) else None
    return None


def _attributes_from_public_title(public_title: str | None, name: str | None) -> list[VariantAttribute]:
    title = (public_title or "").strip()
    if title:
        if " / " in title:
            parts = [part.strip() for part in title.split(" / ") if part.strip()]
            if len(parts) == 2:
                return [
                    VariantAttribute(attribute_name="color", attribute_value=parts[0]),
                    VariantAttribute(attribute_name="size", attribute_value=parts[1]),
                ]
            return [
                VariantAttribute(attribute_name="option", attribute_value=part)
                for part in parts
            ]
        return [VariantAttribute(attribute_name="size", attribute_value=title)]

    full_name = (name or "").strip()
    if full_name and " - " in full_name:
        suffix = full_name.rsplit(" - ", 1)[-1].strip()
        if suffix:
            return [VariantAttribute(attribute_name="size", attribute_value=suffix)]
    if full_name:
        return [VariantAttribute(attribute_name="variant", attribute_value=full_name)]
    return []


def _variants_from_meta(product: dict[str, Any]) -> list[VariantCombination]:
    raw_variants = product.get("variants")
    if not isinstance(raw_variants, list):
        return []

    combinations: list[VariantCombination] = []
    for item in raw_variants:
        if not isinstance(item, dict):
            continue
        attrs = _attributes_from_public_title(
            item.get("public_title") if isinstance(item.get("public_title"), str) else None,
            item.get("name") if isinstance(item.get("name"), str) else None,
        )
        if not attrs:
            continue
        sku = item.get("sku")
        sku_str = sku.strip() if isinstance(sku, str) and sku.strip() else None
        available = item.get("available")
        stock: bool | None
        if isinstance(available, bool):
            stock = available
        else:
            stock = None
        combinations.append(
            VariantCombination(attributes=attrs, sku=sku_str, is_in_stock=stock)
        )
    return combinations


def _selected_variant_from_meta(
    variants: list[VariantCombination],
    *,
    variant_id: str | None,
    raw_variants: list[Any],
) -> list[VariantAttribute] | None:
    if variant_id and raw_variants:
        for item, combo in zip(raw_variants, variants, strict=False):
            if not isinstance(item, dict):
                continue
            if str(item.get("id")) == variant_id:
                return combo.attributes
    for combo in variants:
        if combo.is_in_stock is not False:
            return combo.attributes
    return variants[0].attributes if variants else None


def extract_shopify_meta(html: str, *, url: str) -> ExtractedFields:
    """Extract variant matrix from Shopify ``var meta`` when JSON-LD omits it."""
    product = _parse_meta_json(html)
    if product is None:
        return ExtractedFields()

    raw_variants = product.get("variants")
    if not isinstance(raw_variants, list):
        raw_variants = []

    available_variants = _variants_from_meta(product)
    selected_variant = _selected_variant_from_meta(
        available_variants,
        variant_id=variant_id_from_url(url),
        raw_variants=raw_variants,
    )
    return ExtractedFields(
        available_variants=available_variants,
        selected_variant=selected_variant,
        raw_snapshot={"shopify_variant_count": len(available_variants)},
    )


def merge_shopify_extraction(html: str, *, url: str) -> ExtractedFields:
    """Merge JSON-LD/OG fields with Shopify meta variant data."""
    base = extract_from_html(html)
    meta = extract_shopify_meta(html, url=url)

    if not base.available_variants and meta.available_variants:
        base.available_variants = meta.available_variants
    if base.selected_variant is None and meta.selected_variant is not None:
        base.selected_variant = meta.selected_variant

    if meta.raw_snapshot:
        base.raw_snapshot = {**base.raw_snapshot, **meta.raw_snapshot}
    return base
