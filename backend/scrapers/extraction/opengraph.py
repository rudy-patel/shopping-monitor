"""OpenGraph and product meta tag extraction."""

from __future__ import annotations

from bs4 import BeautifulSoup

from scrapers.extraction.price import normalize_currency, parse_price_cents
from scrapers.extraction.types import ExtractedFields

_META_PROPERTY_MAP = {
    "og:title": "title",
    "og:image": "image_url",
    "og:price:amount": "price",
    "product:price:amount": "price",
    "og:price:currency": "currency",
    "product:price:currency": "currency",
    "product:availability": "availability",
}


def _meta_content(soup: BeautifulSoup, prop: str) -> str | None:
    tag = soup.find("meta", attrs={"property": prop})
    if tag is None:
        tag = soup.find("meta", attrs={"name": prop})
    if tag is None:
        return None
    content = tag.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    return None


def _parse_availability(value: str) -> bool | None:
    text = value.strip().lower()
    if text in {"instock", "in stock", "in_stock"}:
        return True
    if text in {"oos", "out of stock", "outofstock", "out_of_stock"}:
        return False
    return None


def extract_opengraph(html: str) -> ExtractedFields:
    """Extract product fields from OG/product meta tags and <title>."""
    soup = BeautifulSoup(html, "html.parser")
    fields: dict[str, str] = {}

    for prop, field_name in _META_PROPERTY_MAP.items():
        content = _meta_content(soup, prop)
        if content and field_name not in fields:
            fields[field_name] = content

    title = fields.get("title")
    if not title:
        title_tag = soup.find("title")
        if title_tag and title_tag.string and title_tag.string.strip():
            title = title_tag.string.strip()

    price_cents = None
    if "price" in fields:
        price_cents = parse_price_cents(fields["price"])

    currency = normalize_currency(fields.get("currency"))
    is_in_stock = None
    if "availability" in fields:
        is_in_stock = _parse_availability(fields["availability"])

    return ExtractedFields(
        title=title,
        image_url=fields.get("image_url"),
        price_cents=price_cents,
        currency=currency,
        is_in_stock=is_in_stock,
        raw_snapshot={"extraction": "opengraph"},
    )
