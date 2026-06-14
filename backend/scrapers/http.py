"""Canonical HTTP entry point for retailer scrapers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import httpx

from scrapers.exceptions import NetworkBlockedInFixturesError  # pragma: allowlist secret
from scrapers.mode import is_fixtures_mode  # pragma: allowlist secret


@dataclass(frozen=True)
class ScraperResponse:
    status_code: int
    body_text: str
    body_bytes: bytes
    headers: Mapping[str, str]
    final_url: str


def scraper_fetch(
    url: str,
    *,
    retailer_slug: str,
    timeout: float = 15.0,
    headers: Mapping[str, str] | None = None,
) -> ScraperResponse:
    if is_fixtures_mode():  # pragma: allowlist secret
        raise NetworkBlockedInFixturesError(  # pragma: allowlist secret
            "Outbound network requests are blocked in fixture scraper mode.",
            retailer_slug=retailer_slug,
            url=url,
        )

    request_headers = dict(headers) if headers else {}
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        response = client.get(url, headers=request_headers)

    return ScraperResponse(
        status_code=response.status_code,
        body_text=response.text,
        body_bytes=response.content,
        headers=dict(response.headers),
        final_url=str(response.url),
    )
