"""Indigo (Shopify) product extraction with format-variant stock semantics."""

from __future__ import annotations

import json
import re
from typing import Any

from scrapers.contract import VariantAttribute, VariantCombination
from scrapers.extraction.shopify import merge_shopify_extraction
from scrapers.extraction.types import ExtractedFields

_IN_STOCK_MARKERS = frozenset({"instock", "in stock", "onlineonly"})
_OUT_OF_STOCK_MARKERS = frozenset({"outofstock", "out of stock"})


def _availability_from_offer(offers: Any) -> bool | None:
    if isinstance(offers, dict):
        availability = offers.get("availability")
        if isinstance(availability, str):
            lowered = availability.rsplit("/", 1)[-1].lower()
            if lowered in _IN_STOCK_MARKERS:
                return True
            if lowered in _OUT_OF_STOCK_MARKERS:
                return False
    return None


def _variants_from_product_group(node: dict[str, Any]) -> list[VariantCombination]:
    combinations: list[VariantCombination] = []
    for variant in node.get("hasVariant", []):
        if not isinstance(variant, dict):
            continue
        name = variant.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        label = name.split(" - ", 1)[-1].strip() if " - " in name else name.strip()
        stock = _availability_from_offer(variant.get("offers"))
        combinations.append(
            VariantCombination(
                attributes=[VariantAttribute(attribute_name="format", attribute_value=label)],
                sku=variant.get("sku") if isinstance(variant.get("sku"), str) else None,
                is_in_stock=stock,
            )
        )
    return combinations


def _product_group_fields(html: str) -> ExtractedFields | None:
    for raw in re.findall(
        r'<script type="application/ld\+json">(.*?)</script>',
        html,
        flags=re.DOTALL,
    ):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        node_type = data.get("@type")
        if node_type != "ProductGroup":
            continue

        variants = _variants_from_product_group(data)
        if not variants:
            return None

        physical = [
            variant
            for variant in variants
            if variant.attributes
            and variant.attributes[0].attribute_value.lower() != "kobo ebook"
        ]
        preferred = physical or variants
        selected = preferred[0]
        offer = None
        for variant_node in data.get("hasVariant", []):
            if not isinstance(variant_node, dict):
                continue
            name = variant_node.get("name")
            if (
                isinstance(name, str)
                and selected.attributes
                and name.endswith(selected.attributes[0].attribute_value)
            ):
                offer = variant_node.get("offers")
                break

        price_cents = None
        currency = "CAD"
        if isinstance(offer, dict):
            price = offer.get("price")
            if price is not None:
                price_cents = int(round(float(price) * 100))
            currency_raw = offer.get("priceCurrency")
            if isinstance(currency_raw, str) and currency_raw.strip():
                currency = currency_raw.strip().upper()

        in_stock_values = [variant.is_in_stock for variant in preferred]
        if any(value is True for value in in_stock_values):
            is_in_stock = True
        elif any(value is False for value in in_stock_values):
            is_in_stock = False
        else:
            is_in_stock = None

        title = data.get("name")
        title_str = title.strip() if isinstance(title, str) and title.strip() else None
        return ExtractedFields(
            title=title_str,
            price_cents=price_cents,
            currency=currency,
            is_in_stock=is_in_stock,
            available_variants=variants,
            selected_variant=selected.attributes,
            raw_snapshot={"extraction": "indigo_product_group"},
        )
    return None


def merge_indigo_extraction(html: str, url: str) -> ExtractedFields:
    """Merge Shopify meta/JSON-LD with Indigo ProductGroup availability."""
    extracted = merge_shopify_extraction(html, url=url)
    group = _product_group_fields(html)
    if group is None:
        return extracted

    if group.title:
        extracted.title = group.title
    if group.price_cents is not None:
        extracted.price_cents = group.price_cents
    if group.currency:
        extracted.currency = group.currency
    if group.is_in_stock is not None:
        extracted.is_in_stock = group.is_in_stock
    if group.available_variants:
        extracted.available_variants = group.available_variants
    if group.selected_variant:
        extracted.selected_variant = group.selected_variant
    extracted.raw_snapshot.update(group.raw_snapshot)
    return extracted
