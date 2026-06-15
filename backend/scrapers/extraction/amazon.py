"""Amazon.ca product page extraction with first-party seller verification."""

from __future__ import annotations

import html as html_module
import json
import re

from scrapers.contract import VariantAttribute, VariantCombination
from scrapers.exceptions import ScrapeBlockedError
from scrapers.extraction.price import parse_price_cents
from scrapers.extraction.types import ExtractedFields

_AMAZON_CA_FIRST_PARTY_MARKERS = (
    "Sold by Amazon.ca",
    "Ships from and sold by Amazon.ca",
)

_AMAZON_CA_SELLER_SPAN = re.compile(
    r"Sold by:?\s*</span>\s*<span[^>]*>\s*Amazon\.ca\s*</span>",
    re.IGNORECASE,
)

_THIRD_PARTY_SELLER = re.compile(
    r"Sold by:?\s*</span>\s*<span[^>]*>\s*(?!Amazon\.ca)([^<]+)\s*</span>",
    re.IGNORECASE,
)


def is_amazon_ca_first_party(html: str) -> bool:
    """Return True when the listing is sold by Amazon.ca first party."""
    if any(marker in html for marker in _AMAZON_CA_FIRST_PARTY_MARKERS):
        return True
    if _AMAZON_CA_SELLER_SPAN.search(html):
        return True
    return False


def assert_amazon_ca_first_party(html: str, *, url: str) -> None:
    """Reject third-party marketplace listings per PRD §11."""
    if is_amazon_ca_first_party(html):
        return

    availability = _availability_text(html)
    if availability is not None and "unavailable" in availability.lower():
        return

    if _THIRD_PARTY_SELLER.search(html) or re.search(
        r"Sold by\s*<a\b",
        html,
        re.IGNORECASE,
    ):
        raise ScrapeBlockedError(
            "This listing is not sold directly by Amazon.ca. "
            "V1 only tracks Amazon first-party listings.",
            retailer_slug="amazon_ca",
            url=url,
        )

    if _title(html) and _price_cents(html) is not None:
        raise ScrapeBlockedError(
            "Could not verify this listing is sold by Amazon.ca.",
            retailer_slug="amazon_ca",
            url=url,
        )


def _title(html: str) -> str | None:
    match = re.search(
        r'<span id="productTitle"[^>]*>\s*(.*?)\s*</span>',
        html,
        re.DOTALL,
    )
    if match is None:
        return None
    title = re.sub(r"\s+", " ", html_module.unescape(match.group(1))).strip()
    return title or None


def _price_cents(html: str) -> int | None:
    whole = re.search(r'class="a-price-whole">(\d+)', html)
    fraction = re.search(r'class="a-price-fraction">(\d+)', html)
    if whole is not None and fraction is not None:
        return int(whole.group(1)) * 100 + int(fraction.group(1))

    for raw in re.findall(
        r'<script type="application/ld\+json">(.*?)</script>',
        html,
        flags=re.DOTALL,
    ):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        nodes = data if isinstance(data, list) else [data]
        for node in nodes:
            if not isinstance(node, dict) or node.get("@type") != "Product":
                continue
            offers = node.get("offers")
            if isinstance(offers, dict):
                price = offers.get("price")
                if price is not None:
                    cents = parse_price_cents(str(price))
                    if cents is not None:
                        return cents
    return None


def _availability_text(html: str) -> str | None:
    match = re.search(
        r'id="availability"[^>]*>.*?<span[^>]*>([^<]+)</span>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return None
    return html_module.unescape(match.group(1)).strip()


def _is_in_stock(html: str) -> bool:
    availability = _availability_text(html)
    if availability is not None:
        lowered = availability.lower()
        if "unavailable" in lowered:
            return False
        if "in stock" in lowered:
            return True
        if "only" in lowered and "left in stock" in lowered:
            return True
    if _price_cents(html) is not None:
        return True
    return False


def _parse_twister_payload(html: str) -> dict[str, list[str]] | None:
    key = '"dimensionValuesDisplayData" : '
    idx = html.find(key)
    if idx < 0:
        key = '"dimensionValuesDisplayData":'
        idx = html.find(key)
    if idx < 0:
        return None

    start = html.find("{", idx)
    depth = 0
    for index in range(start, min(start + 120_000, len(html))):
        char = html[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(html[start : index + 1])
                except json.JSONDecodeError:
                    return None
                return parsed if isinstance(parsed, dict) else None
    return None


def _parse_twister_variants(html: str) -> list[VariantCombination]:
    payload = _parse_twister_payload(html)
    if not payload:
        return []

    combinations: list[VariantCombination] = []
    for values in payload.values():
        if not isinstance(values, list) or not values:
            continue
        attributes = [
            VariantAttribute(
                attribute_name=f"option_{position + 1}",
                attribute_value=str(value),
            )
            for position, value in enumerate(values)
        ]
        combinations.append(VariantCombination(attributes=attributes))

    return combinations


def _selected_variant(
    html: str,
    url: str,
    variants: list[VariantCombination],
) -> list[VariantAttribute] | None:
    asin_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url, re.IGNORECASE)
    if asin_match is None:
        return variants[0].attributes if len(variants) == 1 else None

    asin = asin_match.group(1).upper()
    payload = _parse_twister_payload(html)
    if isinstance(payload, dict) and asin in payload:
        values = payload[asin]
        if isinstance(values, list) and values:
            return [
                VariantAttribute(
                    attribute_name=f"option_{position + 1}",
                    attribute_value=str(value),
                )
                for position, value in enumerate(values)
            ]

    return variants[0].attributes if len(variants) == 1 else None


def _image_url(html: str) -> str | None:
    match = re.search(r'id="landingImage"[^>]+data-old-hires="([^"]+)"', html)
    if match:
        return match.group(1)
    match = re.search(r'id="imgTagWrapperId"[^>]*>.*?src="([^"]+)"', html, re.DOTALL)
    if match:
        return match.group(1)
    return None


def extract_amazon_html(html: str, url: str) -> ExtractedFields:
    """Extract Amazon.ca product fields from PDP HTML."""
    title = _title(html)
    price_cents = _price_cents(html)
    variants = _parse_twister_variants(html)
    selected = _selected_variant(html, url, variants)

    raw_snapshot: dict[str, object] = {
        "first_party_verified": is_amazon_ca_first_party(html),
    }
    asin_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url, re.IGNORECASE)
    if asin_match:
        raw_snapshot["asin"] = asin_match.group(1).upper()

    return ExtractedFields(
        title=title,
        brand=None,
        image_url=_image_url(html),
        price_cents=price_cents,
        currency="CAD",
        is_in_stock=_is_in_stock(html),
        available_variants=variants,
        selected_variant=selected,
        breadcrumbs=None,
        raw_snapshot=raw_snapshot,
    )


def validate_amazon_listing(
    extracted: ExtractedFields,
    html: str,
    url: str,
) -> None:
    """Post-parse hook enforcing the Amazon.ca first-party rule."""
    assert_amazon_ca_first_party(html, url=url)
