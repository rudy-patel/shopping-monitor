"""Abercrombie & Fitch Canada product page extraction."""

from __future__ import annotations

import re

from scrapers.contract import VariantAttribute, VariantCombination
from scrapers.extraction.embedded_json import parse_js_assignment, parse_price_from_formatted
from scrapers.extraction.types import ExtractedFields
from scrapers.structured_data import extract_from_html


def _primary_product_id(html: str) -> str | None:
    match = re.search(r"productPrices\[(\d+)\]\s*=\s*(\{)", html)
    return match.group(1) if match else None


def _price_from_product_prices(html: str) -> tuple[int | None, str | None]:
    product_id = _primary_product_id(html)
    if product_id is None:
        return None, None

    payload = parse_js_assignment(html, f"productPrices[{product_id}]")
    if payload is None:
        return None, None

    for key in ("contractPriceFmt", "lowContractPriceFmt", "highContractPriceFmt"):
        formatted = payload.get(key)
        if isinstance(formatted, str):
            price_cents = parse_price_from_formatted(formatted)
            if price_cents is not None:
                return price_cents, "CAD"

    items = payload.get("items")
    if isinstance(items, dict):
        for item in items.values():
            if not isinstance(item, dict):
                continue
            formatted = item.get("offerPriceFmt")
            if isinstance(formatted, str):
                price_cents = parse_price_from_formatted(formatted)
                if price_cents is not None:
                    return price_cents, "CAD"

    contract_price = payload.get("contractPrice")
    if isinstance(contract_price, (int, float)):
        return int(round(float(contract_price) * 100)), "CAD"
    return None, None


def _variants_from_page(html: str, *, product_id: str | None) -> list[VariantCombination]:
    if product_id is None:
        return []

    anchor = html.find("primarySizeArray")
    if anchor < 0:
        return []

    skus_anchor = html.find('"skus":[', anchor)
    if skus_anchor < 0:
        return []

    start = html.find("[", skus_anchor)
    depth = 0
    for index in range(start, min(start + 80_000, len(html))):
        char = html[index]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                sku_block = html[start : index + 1]
                break
    else:
        return []

    combinations: list[VariantCombination] = []
    for chunk in sku_block.split('"__typename":"Sku"')[1:]:
        if f'"productId":"{product_id}"' not in chunk:
            continue
        label_match = re.search(r'"fullSizeLabel":"([^"]+)"', chunk)
        status_match = re.search(r'"inventoryStatus":"([^"]+)"', chunk)
        if label_match is None:
            continue
        stock = status_match.group(1) == "Available" if status_match else None
        combinations.append(
            VariantCombination(
                attributes=[
                    VariantAttribute(attribute_name="size", attribute_value=label_match.group(1))
                ],
                is_in_stock=stock,
            )
        )
    return combinations


def extract_abercrombie_html(html: str, url: str) -> ExtractedFields:
    """Extract Abercrombie product fields from JSON-LD plus embedded price JSON."""
    extracted = extract_from_html(html)
    product_id = _primary_product_id(html)

    price_cents, currency = _price_from_product_prices(html)
    if price_cents is not None:
        extracted.price_cents = price_cents
    if currency:
        extracted.currency = currency

    variants = _variants_from_page(html, product_id=product_id)
    if variants:
        extracted.available_variants = variants
        for variant in variants:
            if variant.is_in_stock is True:
                extracted.selected_variant = variant.attributes
                break
        if extracted.selected_variant is None:
            extracted.selected_variant = variants[0].attributes

    statuses = [variant.is_in_stock for variant in variants if variant.is_in_stock is not None]
    if statuses:
        extracted.is_in_stock = any(statuses)
    elif extracted.is_in_stock is None and extracted.price_cents is not None:
        extracted.is_in_stock = True

    extracted.raw_snapshot["extraction"] = "abercrombie"
    extracted.raw_snapshot["url"] = url
    return extracted
