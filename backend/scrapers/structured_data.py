"""Orchestrate JSON-LD and OpenGraph extraction."""

from __future__ import annotations

from scrapers.extraction.jsonld import extract_jsonld
from scrapers.extraction.opengraph import extract_opengraph
from scrapers.extraction.types import ExtractedFields


def extract_from_html(html: str) -> ExtractedFields:
    """Try JSON-LD first, then fall back to OpenGraph/product meta tags."""
    jsonld = extract_jsonld(html)
    if jsonld is not None and jsonld.price_cents is not None:
        return jsonld

    og = extract_opengraph(html)
    if jsonld is not None:
        if og.title and not jsonld.title:
            jsonld.title = og.title
        if og.image_url and not jsonld.image_url:
            jsonld.image_url = og.image_url
        if og.currency and not jsonld.currency:
            jsonld.currency = og.currency
        if og.is_in_stock is not None and jsonld.is_in_stock is None:
            jsonld.is_in_stock = og.is_in_stock
        if og.price_cents is not None:
            jsonld.price_cents = og.price_cents
            jsonld.raw_snapshot = og.raw_snapshot
        return jsonld

    return og
