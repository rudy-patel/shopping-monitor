"""Retailer-specific API sub-probes for http_parse strategy."""

from __future__ import annotations

from collections.abc import Callable

from scrapers.extraction.bestbuy_api import extract_from_product_url_via_api
from scrapers.extraction.types import ExtractedFields

RetailerApiProbe = Callable[[str], ExtractedFields]

RETAILER_API_PROBES: dict[str, RetailerApiProbe] = {
    "bestbuy_ca": extract_from_product_url_via_api,
}

RETAILER_API_NAMES: dict[str, str] = {
    "bestbuy_ca": "bestbuy_json_v2",
}
