"""Helpers for parsing embedded JSON assignments in retailer HTML."""

from __future__ import annotations

import html as html_module
import json
import re
from typing import Any

from scrapers.extraction.price import parse_price_cents


def parse_js_assignment(html: str, variable: str) -> dict[str, Any] | None:
    """Parse ``variable = {...};`` from inline script tags."""
    pattern = rf"{re.escape(variable)}\s*=\s*(\{{)"
    match = re.search(pattern, html)
    if match is None:
        return None

    start = match.start(1)
    depth = 0
    for index in range(start, len(html)):
        char = html[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    payload = json.loads(html[start : index + 1])
                except json.JSONDecodeError:
                    return None
                return payload if isinstance(payload, dict) else None
    return None


def parse_price_from_formatted(value: str | None) -> int | None:
    """Parse retailer price strings such as ``$34.97&nbsp;CAD``."""
    if not value:
        return None
    cleaned = html_module.unescape(value)
    cleaned = cleaned.replace("\xa0", " ")
    match = re.search(r"(\d[\d,]*(?:\.\d+)?)", cleaned)
    if match is None:
        return None
    return parse_price_cents(match.group(1))
