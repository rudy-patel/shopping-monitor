"""Best Buy Canada JSON product API extraction (live/record fallback)."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlsplit

from scrapers.exceptions import ScrapeBlockedError, ScrapeParseError
from scrapers.extraction.price import parse_price_cents
from scrapers.extraction.types import ExtractedFields
from scrapers.http import scraper_fetch

_PRODUCT_ID_RE = re.compile(r"/(\d{5,})(?:[/?#]|$)")
_BESTBUY_PRODUCT_API_URL = "https://www.bestbuy.ca/api/v2/json/product/{product_id}"

_ONLINE_IN_STOCK = frozenset({"InStock", "InStockOnline"})
_ONLINE_OOS = frozenset({"SoldOut", "SoldOutOnline", "NotAvailable", "OutOfStock"})


def product_id_from_url(url: str) -> str | None:
    match = _PRODUCT_ID_RE.search(urlsplit(url).path)
    return match.group(1) if match else None


def fetch_product_payload(product_id: str) -> dict[str, Any]:
    """Fetch Best Buy product JSON for a numeric product id."""
    api_url = _BESTBUY_PRODUCT_API_URL.format(product_id=product_id)
    response = scraper_fetch(api_url, retailer_slug="bestbuy_ca")
    if response.status_code != 200:
        raise ScrapeBlockedError(
            "Best Buy product API returned an error",
            retailer_slug="bestbuy_ca",
            url=api_url,
        )
    try:
        payload = json.loads(response.body_text)
    except json.JSONDecodeError as exc:
        raise ScrapeParseError(
            "Best Buy product API returned invalid JSON",
            retailer_slug="bestbuy_ca",
            url=api_url,
        ) from exc
    if not isinstance(payload, dict):
        raise ScrapeParseError(
            "Best Buy product API returned unexpected payload",
            retailer_slug="bestbuy_ca",
            url=api_url,
        )
    return payload


def extract_from_product_url_via_api(url: str) -> ExtractedFields:
    """Resolve product id from a PDP URL and extract fields from the JSON API."""
    product_id = product_id_from_url(url)
    if not product_id:
        raise ScrapeBlockedError(
            "Couldn't resolve Best Buy product id from URL",
            retailer_slug="bestbuy_ca",
            url=url,
        )
    extracted = extract_bestbuy_api_json(fetch_product_payload(product_id))
    raw_snapshot = dict(extracted.raw_snapshot)
    raw_snapshot["product_id"] = product_id
    raw_snapshot["schema_types"] = ["Product"]
    extracted.raw_snapshot = raw_snapshot
    return extracted


def _online_availability_in_stock(availability: Any) -> bool | None:
    if not isinstance(availability, dict):
        return None
    status = str(availability.get("onlineAvailability") or "").strip()
    if status in _ONLINE_IN_STOCK:
        return True
    if status in _ONLINE_OOS:
        return False
    if availability.get("isAvailableOnline") is True:
        return True
    if availability.get("isAvailableOnline") is False:
        return False
    return None


def _brand_title(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    if not cleaned or cleaned.upper() == "N/A":
        return None
    return cleaned.title() if cleaned.isupper() else cleaned


def _image_url(data: dict[str, Any]) -> str | None:
    for key in ("highResImage", "thumbnailImage"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    additional = data.get("additionalMedia")
    if isinstance(additional, list):
        for item in additional:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            if isinstance(url, str) and url.strip():
                return url.strip()
    return None


def extract_bestbuy_api_json(data: dict[str, Any]) -> ExtractedFields:
    """Map Best Buy ``/api/v2/json/product/{sku}`` payload to extracted fields."""
    title = data.get("name")
    title_str = title.strip() if isinstance(title, str) and title.strip() else None

    price_raw = data.get("salePrice")
    if price_raw is None:
        price_raw = data.get("regularPrice")
    price_cents = parse_price_cents(price_raw) if price_raw is not None else None

    brand = _brand_title(data.get("brandName"))
    image_url = _image_url(data)
    stock = _online_availability_in_stock(data.get("availability"))

    breadcrumbs: list[str] = []
    category = data.get("categoryName")
    if isinstance(category, str) and category.strip():
        breadcrumbs.append(category.strip())

    sku_raw = data.get("sku")
    sku = sku_raw.strip() if isinstance(sku_raw, str) and sku_raw.strip() else None

    return ExtractedFields(
        title=title_str,
        brand=brand,
        image_url=image_url,
        price_cents=price_cents,
        currency="CAD",
        is_in_stock=stock,
        breadcrumbs=breadcrumbs,
        raw_snapshot={
            "extraction": "bestbuy_api",
            "sku": sku,
            "product_id": sku,
        },
    )


def json_api_to_fixture_html(data: dict[str, Any]) -> str:
    """Build minimal HTML with JSON-LD so fixture-mode tests use the HTML path."""
    extracted = extract_bestbuy_api_json(data)
    if not extracted.title or extracted.price_cents is None:
        raise ValueError("API payload missing title or price for fixture HTML")

    price_dollars = extracted.price_cents / 100
    availability = (
        "https://schema.org/InStock"
        if extracted.is_in_stock is not False
        else "https://schema.org/OutOfStock"
    )
    jsonld: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": extracted.title,
        "sku": extracted.raw_snapshot.get("sku"),
        "offers": {
            "@type": "Offer",
            "price": f"{price_dollars:.2f}",
            "priceCurrency": "CAD",
            "availability": availability,
        },
    }
    if extracted.brand:
        jsonld["brand"] = {"@type": "Brand", "name": extracted.brand}
    if extracted.image_url:
        jsonld["image"] = extracted.image_url

    return (
        "<!DOCTYPE html><html><head>"
        f'<script type="application/ld+json">{json.dumps(jsonld)}</script>'
        "</head><body><!-- bestbuy_api fixture --></body></html>"
    )
