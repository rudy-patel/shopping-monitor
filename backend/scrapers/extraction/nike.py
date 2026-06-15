"""Nike Canada product page extraction from ``__NEXT_DATA__``."""

from __future__ import annotations

import json
import re

from scrapers.contract import VariantAttribute, VariantCombination
from scrapers.extraction.types import ExtractedFields


def _parse_next_data(html: str) -> dict | None:
    match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if match is None:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    page_props = data.get("props", {}).get("pageProps", {})
    return page_props if isinstance(page_props, dict) else None


def _price_cents(selected_product: dict) -> int | None:
    prices = selected_product.get("prices")
    if not isinstance(prices, dict):
        return None
    current = prices.get("currentPrice")
    if isinstance(current, (int, float)):
        return int(round(float(current) * 100))
    return None


def _color_variants(page_props: dict) -> list[VariantCombination]:
    combinations: list[VariantCombination] = []
    groups = page_props.get("productGroups")
    if not isinstance(groups, list) or not groups:
        return combinations

    products = groups[0].get("products")
    if not isinstance(products, dict):
        return combinations

    for style_color, product in products.items():
        if not isinstance(product, dict):
            continue
        color_desc = product.get("colorDescription")
        label = color_desc if isinstance(color_desc, str) and color_desc else style_color
        combinations.append(
            VariantCombination(
                attributes=[VariantAttribute(attribute_name="color", attribute_value=label)],
                sku=style_color if isinstance(style_color, str) else None,
            )
        )
    return combinations


def _size_variants(selected_product: dict) -> list[VariantCombination]:
    sizes = selected_product.get("sizes")
    if not isinstance(sizes, list):
        return []

    combinations: list[VariantCombination] = []
    for entry in sizes:
        if not isinstance(entry, dict):
            continue
        localized = entry.get("localizedLabel") or entry.get("label")
        if not isinstance(localized, str) or not localized.strip():
            continue
        stock = entry.get("status") == "ACTIVE"
        combinations.append(
            VariantCombination(
                attributes=[
                    VariantAttribute(attribute_name="size", attribute_value=localized.strip())
                ],
                is_in_stock=stock,
            )
        )
    return combinations


def _selected_variant(
    page_props: dict,
    selected_product: dict,
) -> list[VariantAttribute] | None:
    style_color = page_props.get("styleColor") or selected_product.get("styleColor")
    color_desc = selected_product.get("colorDescription")
    attributes: list[VariantAttribute] = []

    if isinstance(color_desc, str) and color_desc.strip():
        attributes.append(
            VariantAttribute(attribute_name="color", attribute_value=color_desc.strip())
        )
    elif isinstance(style_color, str) and style_color.strip():
        attributes.append(
            VariantAttribute(attribute_name="color", attribute_value=style_color.strip())
        )

    selected_sku = selected_product.get("selectedSku")
    sizes = selected_product.get("sizes")
    if isinstance(sizes, list) and isinstance(selected_sku, str):
        for entry in sizes:
            if not isinstance(entry, dict):
                continue
            merch = entry.get("merchSkuId")
            if merch == selected_sku:
                localized = entry.get("localizedLabel") or entry.get("label")
                if isinstance(localized, str) and localized.strip():
                    attributes.append(
                        VariantAttribute(
                            attribute_name="size",
                            attribute_value=localized.strip(),
                        )
                    )
                break

    return attributes or None


def _is_in_stock(selected_product: dict) -> bool:
    sizes = selected_product.get("sizes")
    if isinstance(sizes, list) and sizes:
        return any(
            isinstance(entry, dict) and entry.get("status") == "ACTIVE" for entry in sizes
        )
    return True


def _image_url(selected_product: dict) -> str | None:
    images = selected_product.get("contentImages")
    if isinstance(images, list):
        for image in images:
            if isinstance(image, dict):
                url = image.get("url") or image.get("src")
                if isinstance(url, str) and url.startswith("http"):
                    return url
    return None


def extract_nike_html(html: str, _url: str) -> ExtractedFields:
    """Extract Nike.ca product fields from PDP HTML."""
    page_props = _parse_next_data(html)
    if page_props is None:
        return ExtractedFields()

    selected = page_props.get("selectedProduct")
    if not isinstance(selected, dict):
        return ExtractedFields()

    product_info = selected.get("productInfo")
    title = None
    if isinstance(product_info, dict):
        title = product_info.get("fullTitle") or product_info.get("title")
        if isinstance(title, str):
            title = title.strip()

    color_variants = _color_variants(page_props)
    size_variants = _size_variants(selected)
    variants = color_variants if len(color_variants) >= 2 else size_variants

    style_color = page_props.get("styleColor") or selected.get("styleColor")
    raw_snapshot: dict[str, object] = {}
    if isinstance(style_color, str):
        raw_snapshot["style_color"] = style_color

    return ExtractedFields(
        title=title,
        brand="Nike",
        image_url=_image_url(selected),
        price_cents=_price_cents(selected),
        currency="CAD",
        is_in_stock=_is_in_stock(selected),
        available_variants=variants,
        selected_variant=_selected_variant(page_props, selected),
        breadcrumbs=None,
        raw_snapshot=raw_snapshot,
    )
