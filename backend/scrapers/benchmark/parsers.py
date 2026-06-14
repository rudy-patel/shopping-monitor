"""Retailer-specific HTML parsers for the benchmark harness."""

from __future__ import annotations

from collections.abc import Callable

from scrapers.bestbuy_ca import extract_bestbuy_html
from scrapers.extraction.abercrombie import extract_abercrombie_html
from scrapers.extraction.apple import extract_apple_html
from scrapers.extraction.indigo import merge_indigo_extraction
from scrapers.extraction.shopify import merge_shopify_extraction
from scrapers.extraction.types import ExtractedFields
from scrapers.structured_data import extract_from_html

ParserFn = Callable[[str, str], ExtractedFields]


def _generic_parser(html: str, _url: str) -> ExtractedFields:
    return extract_from_html(html)


def _bestbuy_parser(html: str, url: str) -> ExtractedFields:
    return extract_bestbuy_html(html, url=url)


def _shopify_parser(html: str, url: str) -> ExtractedFields:
    return merge_shopify_extraction(html, url=url)


PARSER_BY_SLUG: dict[str, ParserFn] = {
    "generic": _generic_parser,
    "bestbuy_ca": _bestbuy_parser,
    "palmisleskate": _shopify_parser,
    "tikiroomskate": _shopify_parser,
    "indigo": merge_indigo_extraction,
    "apple_ca": extract_apple_html,
    "abercrombie": extract_abercrombie_html,
}


def get_parser(slug: str) -> ParserFn:
    try:
        return PARSER_BY_SLUG[slug]
    except KeyError as exc:
        raise ValueError(f"No benchmark parser registered for slug {slug!r}") from exc
