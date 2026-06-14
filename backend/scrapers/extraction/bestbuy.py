"""Best Buy Canada embedded state extraction."""

from __future__ import annotations

import json
import re
from typing import Any

from scrapers.contract import VariantAttribute, VariantCombination
from scrapers.extraction.types import ExtractedFields

_INITIAL_STATE_RE = re.compile(
    r"window\.__INITIAL_STATE__ = (\{.*?\});\s*\n\s*window\.__REACT_QUERY_STATE__",
    re.DOTALL,
)

_OUT_OF_STOCK_SHIPPING = frozenset({"SoldOutOnline", "NotAvailable", "OutOfStock"})


def _parse_initial_state(html: str) -> dict[str, Any] | None:
    match = _INITIAL_STATE_RE.search(html)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _attribute_name(label: str) -> str:
    normalized = label.strip().lower()
    if normalized == "colour family":
        return "color"
    return normalized


def _variants_from_product_variants(product_variants: Any) -> list[VariantCombination]:
    if not isinstance(product_variants, list):
        return []

    best_group: list[dict[str, Any]] = []
    for group in product_variants:
        if not isinstance(group, list):
            group = [group]
        skus = {
            str(item.get("sku")).strip()
            for item in group
            if isinstance(item, dict) and item.get("sku")
        }
        if len(skus) >= 2 and len(group) >= len(best_group):
            best_group = [item for item in group if isinstance(item, dict)]

    variants: list[VariantCombination] = []
    for item in best_group:
        label = item.get("label")
        value = item.get("value")
        sku = item.get("sku")
        attrs: list[VariantAttribute] = []
        if isinstance(label, str) and isinstance(value, str) and value.strip():
            attrs.append(
                VariantAttribute(
                    attribute_name=_attribute_name(label),
                    attribute_value=value.strip(),
                )
            )
        sku_str = str(sku).strip() if sku is not None else None
        if attrs or sku_str:
            variants.append(
                VariantCombination(attributes=attrs, sku=sku_str, is_in_stock=None)
            )
    return variants


def _shipping_in_stock(shipping: Any) -> bool | None:
    if not isinstance(shipping, dict):
        return None
    purchasable = shipping.get("purchasable")
    status = str(shipping.get("status") or "").strip()
    if purchasable is True:
        return True
    if purchasable is False or status in _OUT_OF_STOCK_SHIPPING:
        return False
    return None


def extract_bestbuy_embedded(html: str) -> ExtractedFields | None:
    """Extract stock and variant metadata from Best Buy embedded page state."""
    state = _parse_initial_state(html)
    if state is None:
        return None

    product_state = state.get("product")
    if not isinstance(product_state, dict):
        return None

    product = product_state.get("product")
    availability = product_state.get("availability")
    if not isinstance(product, dict):
        product = {}
    if not isinstance(availability, dict):
        availability = {}

    sku_raw = product.get("sku")
    sku = sku_raw.strip() if isinstance(sku_raw, str) and sku_raw.strip() else None
    stock = _shipping_in_stock(availability.get("shipping"))
    variants = _variants_from_product_variants(product.get("productVariants"))

    return ExtractedFields(
        is_in_stock=stock,
        available_variants=variants,
        raw_snapshot={
            "extraction": "bestbuy_embedded",
            "sku": sku,
        },
    )
