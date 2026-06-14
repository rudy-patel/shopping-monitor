"""Price string parsing and currency normalization."""

from __future__ import annotations

import re

_PRICE_STRIP_RE = re.compile(r"[$,\s]")


def parse_price_cents(value: str | int | float) -> int | None:
    """Convert a price string or number to integer cents."""
    if isinstance(value, (int, float)):
        return round(float(value) * 100)

    cleaned = _PRICE_STRIP_RE.sub("", str(value).strip())
    if not cleaned:
        return None
    try:
        return round(float(cleaned) * 100)
    except ValueError:
        return None


def normalize_currency(value: str | None) -> str | None:
    """Normalize currency to 3-letter uppercase ISO 4217."""
    if not value:
        return None
    normalized = value.strip().upper()
    if len(normalized) == 3 and normalized.isalpha():
        return normalized
    return None
