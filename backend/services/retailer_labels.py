"""Human-readable retailer labels — kept in parity with frontend/src/lib/format.ts."""

from __future__ import annotations

from urllib.parse import urlsplit

_RETAILER_LABELS: dict[str, str] = {
    "bestbuy_ca": "Best Buy Canada",
    "indigo": "Indigo",
    "apple_ca": "Apple Canada",
    "abercrombie": "Abercrombie & Fitch",
    "amazon_ca": "Amazon.ca",
    "nike_ca": "Nike Canada",
    "palmisleskate": "Palm Isle Skate Shop",
    "tikiroomskate": "Tiki Room Skateboards",
}


def label_for_slug(slug: str) -> str:
    """Return a friendly label for a registered retailer slug."""
    if slug == "generic":
        return "Other retailer"
    return _RETAILER_LABELS.get(slug, slug.replace("_", " ").title())


def label_from_url(url: str, *, fallback: str | None = None) -> str:
    """Best-effort retailer label from a URL hostname when slug is `generic`."""
    if fallback:
        cleaned = fallback.strip()
        if cleaned:
            return cleaned
    host = (urlsplit(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return "Unknown retailer"
    # walmart.ca → Walmart, londondrugs.com → London Drugs, hbc.com → HBC
    primary = host.split(".")[0]
    if not primary:
        return host
    return primary.replace("-", " ").title()
