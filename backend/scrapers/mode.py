"""Scraper mode resolution from SCRAPER_MODE environment variable."""

from __future__ import annotations

import os
from enum import Enum

from core.settings import DEFAULT_SCRAPER_MODE
from scrapers.exceptions import ScraperConfigError

# TODO(T1.2): proxy to core.settings.get_settings().scraper_mode once all
# scraper code imports the central settings loader.

SCRAPER_MODE_ENV_VAR = "SCRAPER_MODE"  # pragma: allowlist secret


class ScraperMode(str, Enum):
    FIXTURES = DEFAULT_SCRAPER_MODE  # pragma: allowlist secret
    LIVE = "live"
    RECORD = "record"


def get_scraper_mode() -> ScraperMode:
    raw = os.getenv(SCRAPER_MODE_ENV_VAR, ScraperMode.FIXTURES.value)  # pragma: allowlist secret
    normalized = raw.strip().lower()
    try:
        return ScraperMode(normalized)
    except ValueError as exc:
        raise ScraperConfigError(
            f"Invalid {SCRAPER_MODE_ENV_VAR}: {raw!r}. "
            f"Expected one of: {', '.join(m.value for m in ScraperMode)}."
        ) from exc


def is_fixtures_mode() -> bool:  # pragma: allowlist secret
    return get_scraper_mode() == ScraperMode.FIXTURES  # pragma: allowlist secret


def require_fixtures_mode() -> None:  # pragma: allowlist secret
    if not is_fixtures_mode():  # pragma: allowlist secret
        raise ScraperConfigError(
            f"Expected {SCRAPER_MODE_ENV_VAR}={ScraperMode.FIXTURES.value!r}, "  # pragma: allowlist secret
            f"got {get_scraper_mode().value!r}."
        )
