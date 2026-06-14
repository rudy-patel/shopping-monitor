"""Apple Canada buy-flow and product page extraction."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from scrapers.contract import VariantAttribute, VariantCombination
from scrapers.extraction.jsonld import extract_jsonld
from scrapers.extraction.price import parse_price_cents
from scrapers.extraction.types import ExtractedFields
from scrapers.structured_data import extract_from_html


def _is_buy_config_url(url: str) -> bool:
    """True for a specific storage/color config page (not the model picker)."""
    segments = [segment for segment in urlsplit(url).path.split("/") if segment]
    for index, segment in enumerate(segments):
        if segment.startswith("buy-"):
            return len(segments) > index + 2
    return False


def _parse_config_variants(html: str) -> list[VariantCombination]:
    combinations: list[VariantCombination] = []
    seen: set[tuple[str, str, str]] = set()

    pattern = re.compile(
        r'<span class="dimensionCapacity">(\d+).*?</span>\s*'
        r'<span class="dimensionColor">([^<]+)</span>.*?'
        r'<span class="current_price">\$([0-9,]+\.[0-9]{2})</span>',
        flags=re.DOTALL,
    )
    for match in pattern.finditer(html):
        capacity, color, price = match.groups()
        key = (capacity, color.strip(), price)
        if key in seen:
            continue
        seen.add(key)
        price_cents = parse_price_cents(price)
        combinations.append(
            VariantCombination(
                attributes=[
                    VariantAttribute(attribute_name="storage", attribute_value=f"{capacity}GB"),
                    VariantAttribute(attribute_name="color", attribute_value=color.strip()),
                ],
                is_in_stock=True if price_cents is not None else None,
            )
        )
    return combinations


def extract_apple_html(html: str, url: str) -> ExtractedFields:
    """Extract Apple product fields from JSON-LD plus buy-flow HTML."""
    extracted = extract_from_html(html)
    jsonld = extract_jsonld(html)

    if jsonld is not None:
        if jsonld.title and not extracted.title:
            extracted.title = jsonld.title
        if jsonld.price_cents is not None:
            extracted.price_cents = jsonld.price_cents
        if jsonld.currency:
            extracted.currency = jsonld.currency
        if jsonld.image_url:
            extracted.image_url = jsonld.image_url
        if jsonld.brand:
            extracted.brand = jsonld.brand
        if jsonld.available_variants:
            extracted.available_variants = jsonld.available_variants
        if jsonld.selected_variant:
            extracted.selected_variant = jsonld.selected_variant

    if not _is_buy_config_url(url):
        variants = _parse_config_variants(html)
        if variants:
            extracted.available_variants = variants
            extracted.selected_variant = variants[0].attributes

    if jsonld is not None and jsonld.is_in_stock is not None:
        extracted.is_in_stock = jsonld.is_in_stock
    elif extracted.is_in_stock is None and extracted.price_cents is not None:
        extracted.is_in_stock = True

    extracted.raw_snapshot["extraction"] = "apple_ca"
    extracted.raw_snapshot["url"] = url
    return extracted
