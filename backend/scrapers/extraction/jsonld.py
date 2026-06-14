"""Schema.org Product JSON-LD extraction."""

from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup

from scrapers.contract import VariantAttribute, VariantCombination
from scrapers.extraction.price import normalize_currency, parse_price_cents
from scrapers.extraction.types import ExtractedFields

_IN_STOCK_MARKERS = frozenset(
    {
        "https://schema.org/instock",
        "http://schema.org/instock",
        "https://schema.org/onlineonly",
        "http://schema.org/onlineonly",
        "instock",
        "in stock",
        "onlineonly",
    }
)
_OUT_OF_STOCK_MARKERS = frozenset(
    {
        "https://schema.org/outofstock",
        "http://schema.org/outofstock",
        "https://schema.org/discontinued",
        "http://schema.org/discontinued",
        "outofstock",
        "out of stock",
        "discontinued",
    }
)


def _type_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.rsplit("/", 1)[-1].lower()
    return None


def _is_aggregate_offer(offer_type: Any) -> bool:
    if isinstance(offer_type, list):
        return any(_is_aggregate_offer(item) for item in offer_type)
    name = _type_name(offer_type)
    return name == "aggregateoffer"


def _is_product_type(node: dict[str, Any]) -> bool:
    node_type = node.get("@type")
    if node_type is None:
        return False
    if isinstance(node_type, str):
        return node_type.lower() == "product"
    if isinstance(node_type, list):
        return any(isinstance(t, str) and t.lower() == "product" for t in node_type)
    return False


def _iter_jsonld_nodes(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            nodes: list[dict[str, Any]] = []
            for item in data["@graph"]:
                if isinstance(item, dict):
                    nodes.append(item)
            return nodes
        return [data]
    if isinstance(data, list):
        nodes = []
        for item in data:
            if isinstance(item, dict):
                nodes.extend(_iter_jsonld_nodes(item))
        return nodes
    return []


def _parse_availability(value: Any) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in _IN_STOCK_MARKERS:
        return True
    if text in _OUT_OF_STOCK_MARKERS:
        return False
    return None


def _extract_brand(brand: Any) -> str | None:
    if brand is None:
        return None
    if isinstance(brand, str):
        return brand.strip() or None
    if isinstance(brand, dict):
        name = brand.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def _extract_image(image: Any) -> str | None:
    if image is None:
        return None
    if isinstance(image, str) and image.strip():
        return image.strip()
    if isinstance(image, list):
        for item in image:
            url = _extract_image(item)
            if url:
                return url
    if isinstance(image, dict):
        url = image.get("url") or image.get("@id")
        if isinstance(url, str) and url.strip():
            return url.strip()
    return None


def _offer_price_and_currency(offers: Any) -> tuple[int | None, str | None]:
    if offers is None:
        return None, None
    if isinstance(offers, list):
        for offer in offers:
            price_cents, currency = _offer_price_and_currency(offer)
            if price_cents is not None:
                return price_cents, currency
        return None, None
    if not isinstance(offers, dict):
        return None, None

    currency = normalize_currency(offers.get("priceCurrency"))
    price_raw = offers.get("price")
    if price_raw is None and _is_aggregate_offer(offers.get("@type")):
        price_raw = offers.get("lowPrice")
    price_cents = parse_price_cents(price_raw) if price_raw is not None else None
    return price_cents, currency


def _offer_availability(offers: Any) -> bool | None:
    if offers is None:
        return None
    if isinstance(offers, list):
        for offer in offers:
            availability = _offer_availability(offer)
            if availability is not None:
                return availability
        return None
    if isinstance(offers, dict):
        return _parse_availability(offers.get("availability"))
    return None


def _variant_attributes(node: dict[str, Any]) -> list[VariantAttribute]:
    attrs: list[VariantAttribute] = []
    for key in ("color", "size", "material", "pattern"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            attrs.append(VariantAttribute(attribute_name=key, attribute_value=value.strip()))
    return attrs


def _extract_variants(product: dict[str, Any]) -> list[VariantCombination]:
    variants: list[VariantCombination] = []
    has_variant = product.get("hasVariant")
    if has_variant is None:
        return variants
    if not isinstance(has_variant, list):
        has_variant = [has_variant]

    for item in has_variant:
        if not isinstance(item, dict):
            continue
        attrs = _variant_attributes(item)
        if not attrs:
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                attrs = [VariantAttribute(attribute_name="variant", attribute_value=name.strip())]
        sku = item.get("sku")
        sku_str = sku.strip() if isinstance(sku, str) and sku.strip() else None
        offers = item.get("offers")
        stock = _offer_availability(offers)
        if attrs:
            variants.append(
                VariantCombination(attributes=attrs, sku=sku_str, is_in_stock=stock)
            )
    return variants


def _flatten_breadcrumb_items(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    flat: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, list):
            flat.extend(_flatten_breadcrumb_items(item))
        elif isinstance(item, dict):
            flat.append(item)
    return flat


def _extract_breadcrumbs(soup: BeautifulSoup) -> list[str]:
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in _iter_jsonld_nodes(data):
            node_type = node.get("@type")
            types = (
                [node_type]
                if isinstance(node_type, str)
                else node_type
                if isinstance(node_type, list)
                else []
            )
            if not any(isinstance(t, str) and t.lower() == "breadcrumblist" for t in types):
                continue
            items = node.get("itemListElement")
            if not isinstance(items, list):
                continue
            crumbs: list[str] = []
            for item in _flatten_breadcrumb_items(items):
                name = item.get("name")
                if not isinstance(name, str) or not name.strip():
                    nested = item.get("item")
                    if isinstance(nested, dict):
                        nested_name = nested.get("name")
                        if isinstance(nested_name, str):
                            name = nested_name
                if isinstance(name, str) and name.strip():
                    crumbs.append(name.strip())
            if crumbs:
                return crumbs
    return []


def collect_schema_types(html: str) -> list[str]:
    """Collect unique schema.org @type values from JSON-LD blocks."""
    soup = BeautifulSoup(html, "html.parser")
    types: list[str] = []
    seen: set[str] = set()
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in _iter_jsonld_nodes(data):
            node_type = node.get("@type")
            candidates = (
                [node_type]
                if isinstance(node_type, str)
                else node_type
                if isinstance(node_type, list)
                else []
            )
            for candidate in candidates:
                if not isinstance(candidate, str):
                    continue
                name = candidate.rsplit("/", 1)[-1]
                if name and name not in seen:
                    seen.add(name)
                    types.append(name)
    return types


def _product_from_node(node: dict[str, Any]) -> ExtractedFields | None:
    if not _is_product_type(node):
        return None

    title = node.get("name")
    title_str = title.strip() if isinstance(title, str) and title.strip() else None
    brand = _extract_brand(node.get("brand"))
    image_url = _extract_image(node.get("image"))
    price_cents, currency = _offer_price_and_currency(node.get("offers"))
    is_in_stock = _offer_availability(node.get("offers"))
    available_variants = _extract_variants(node)

    sku_raw = node.get("sku")
    sku = sku_raw.strip() if isinstance(sku_raw, str) and sku_raw.strip() else None

    return ExtractedFields(
        title=title_str,
        brand=brand,
        image_url=image_url,
        price_cents=price_cents,
        currency=currency,
        is_in_stock=is_in_stock,
        available_variants=available_variants,
        raw_snapshot={"extraction": "jsonld", "sku": sku},
    )


def _select_best_product(products: list[ExtractedFields]) -> ExtractedFields | None:
    for product in products:
        if product.price_cents is not None:
            return product
    return products[0] if products else None


def extract_jsonld(html: str) -> ExtractedFields | None:
    """Extract product fields from schema.org JSON-LD blocks."""
    soup = BeautifulSoup(html, "html.parser")
    products: list[ExtractedFields] = []

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in _iter_jsonld_nodes(data):
            extracted = _product_from_node(node)
            if extracted is not None:
                products.append(extracted)

    best = _select_best_product(products)
    if best is None:
        return None

    breadcrumbs = _extract_breadcrumbs(soup)
    if breadcrumbs:
        best.breadcrumbs = breadcrumbs
    return best
