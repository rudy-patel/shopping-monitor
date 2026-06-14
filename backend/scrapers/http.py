"""Canonical HTTP entry point for retailer scrapers."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

import httpx

from scrapers.exceptions import (
    NetworkBlockedInFixturesError,  # pragma: allowlist secret
    ScrapeBlockedError,
)
from scrapers.mode import is_fixtures_mode  # pragma: allowlist secret

_DEFAULT_HEADERS: Mapping[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-CA,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_BLOCKED_STATUS_CODES = frozenset({403, 429, 503})
_BLOCKED_BODY_MARKERS = (
    re.compile(r"cf-browser-verification", re.I),
    re.compile(r"cloudflare", re.I),
    re.compile(r"attention required", re.I),
    re.compile(r"access denied", re.I),
    re.compile(r"captcha", re.I),
    re.compile(r"challenge-platform", re.I),
)


@dataclass(frozen=True)
class ScraperResponse:
    status_code: int
    body_text: str
    body_bytes: bytes
    headers: Mapping[str, str]
    final_url: str


def _merge_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    merged = dict(_DEFAULT_HEADERS)
    if headers:
        merged.update(headers)
    return merged


def _looks_blocked(status_code: int, body_text: str) -> bool:
    if status_code not in _BLOCKED_STATUS_CODES:
        return False
    if len(body_text.strip()) < 200:
        return True
    return any(pattern.search(body_text) for pattern in _BLOCKED_BODY_MARKERS)


def _raise_if_blocked(
    *,
    status_code: int,
    body_text: str,
    retailer_slug: str,
    url: str,
) -> None:
    if _looks_blocked(status_code, body_text):
        raise ScrapeBlockedError(
            "Retailer returned a blocked or challenge response",
            retailer_slug=retailer_slug,
            url=url,
        )


def _fetch_with_curl_cffi(
    url: str,
    *,
    timeout: float,
    headers: dict[str, str],
) -> ScraperResponse:
    from curl_cffi import requests as curl_requests

    response = curl_requests.get(
        url,
        impersonate="chrome",
        timeout=timeout,
        headers=headers,
        allow_redirects=True,
    )
    body_bytes = response.content if isinstance(response.content, bytes) else b""
    body_text = response.text if isinstance(response.text, str) else body_bytes.decode(
        "utf-8", errors="replace"
    )
    response_headers = {
        str(key): str(value) for key, value in dict(response.headers).items()
    }
    final_url = str(response.url) if response.url is not None else url
    return ScraperResponse(
        status_code=int(response.status_code),
        body_text=body_text,
        body_bytes=body_bytes,
        headers=response_headers,
        final_url=final_url,
    )


def _fetch_with_httpx(
    url: str,
    *,
    timeout: float,
    headers: dict[str, str],
) -> ScraperResponse:
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        response = client.get(url, headers=headers)

    return ScraperResponse(
        status_code=response.status_code,
        body_text=response.text,
        body_bytes=response.content,
        headers=dict(response.headers),
        final_url=str(response.url),
    )


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

    request_headers = _merge_headers(headers)
    try:
        response = _fetch_with_curl_cffi(
            url,
            timeout=timeout,
            headers=request_headers,
        )
    except Exception:
        response = _fetch_with_httpx(
            url,
            timeout=timeout,
            headers=request_headers,
        )

    _raise_if_blocked(
        status_code=response.status_code,
        body_text=response.body_text,
        retailer_slug=retailer_slug,
        url=url,
    )
    return response
