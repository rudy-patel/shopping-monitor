"""Resolve fixture URLs to scenario names."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from scrapers.exceptions import FixtureNotFoundError

_FIXTURE_HOST = "fixtures.local"
_SCENARIO_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def resolve_fixture_scenario(url: str, retailer_slug: str) -> str:
    """Map ``https://fixtures.local/<retailer_slug>/<scenario>`` to scenario name."""
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if host != _FIXTURE_HOST:
        raise FixtureNotFoundError(
            f"Fixture URL host must be {_FIXTURE_HOST!r}, got {host!r}",
            retailer_slug=retailer_slug,
            url=url,
        )

    path = parsed.path.strip("/")
    parts = path.split("/") if path else []
    if len(parts) != 2 or parts[0] != retailer_slug:
        raise FixtureNotFoundError(
            f"Fixture URL path must be /{retailer_slug}/<scenario>, got {parsed.path!r}",
            retailer_slug=retailer_slug,
            url=url,
        )

    scenario = parts[1]
    if not _SCENARIO_RE.match(scenario):
        raise FixtureNotFoundError(
            f"Invalid fixture scenario name: {scenario!r}",
            retailer_slug=retailer_slug,
            url=url,
        )
    return scenario
