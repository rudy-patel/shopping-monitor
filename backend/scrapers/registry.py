"""In-process retailer scraper registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal
from urllib.parse import urlsplit

from scrapers.contract import ProductSnapshot, ScrapeSource
from scrapers.exceptions import RetailerAlreadyRegisteredError, RetailerNotSupportedError

_REGISTRY: dict[str, "RetailerEntry"] = {}


@dataclass(frozen=True)
class RetailerEntry:
    slug: str
    domains: tuple[str, ...]
    default_category: Literal["clothing", "shoes", "home", "tech", "other"]
    scrape: Callable[[str], ProductSnapshot]
    default_strategy: ScrapeSource
    fallback_strategies: tuple[ScrapeSource, ...] = ()
    fixture_dir: str | None = None


def register(entry: RetailerEntry) -> None:
    if entry.slug in _REGISTRY:
        raise RetailerAlreadyRegisteredError(
            f"Retailer {entry.slug!r} is already registered.",
            retailer_slug=entry.slug,
        )
    _REGISTRY[entry.slug] = entry


def get(slug: str) -> RetailerEntry:
    try:
        return _REGISTRY[slug]
    except KeyError as exc:
        raise RetailerNotSupportedError(
            f"Retailer {slug!r} is not registered.",
            retailer_slug=slug,
        ) from exc


def _normalize_host(host: str) -> str:
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _host_matches_domain(host: str, domain: str) -> bool:
    domain = domain.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return host == domain or host.endswith("." + domain)


def lookup_by_url(url: str) -> RetailerEntry:
    parsed = urlsplit(url)
    host = _normalize_host(parsed.hostname or "")
    if not host:
        raise RetailerNotSupportedError(
            f"Could not parse host from URL: {url!r}",
            url=url,
        )

    for entry in _REGISTRY.values():
        if entry.slug == "generic":
            continue
        for domain in entry.domains:
            if _host_matches_domain(host, domain):
                return entry

    if "generic" in _REGISTRY:
        return _REGISTRY["generic"]

    raise RetailerNotSupportedError(
        f"No registered retailer matches URL: {url!r}",
        url=url,
    )


def all_retailers() -> list[RetailerEntry]:
    return list(_REGISTRY.values())


def reset_registry() -> None:
    """Clear all registered retailers. Test-only."""
    _REGISTRY.clear()
