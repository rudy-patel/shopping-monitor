"""Scraper mode resolution via central settings (T1.2)."""

from __future__ import annotations

from enum import Enum

from pydantic import ValidationError

from core.settings import DEFAULT_SCRAPER_MODE, get_settings
from scrapers.exceptions import ScraperConfigError

SCRAPER_MODE_ENV_VAR = "SCRAPER_MODE"  # pragma: allowlist secret


class ScraperMode(str, Enum):
    FIXTURES = DEFAULT_SCRAPER_MODE  # pragma: allowlist secret
    LIVE = "live"
    RECORD = "record"


def get_scraper_mode() -> ScraperMode:
    try:
        mode = get_settings().scraper_mode
    except ValidationError as exc:
        raise ScraperConfigError("Invalid scraper mode configuration.") from exc
    return ScraperMode(mode)


def is_fixtures_mode() -> bool:  # pragma: allowlist secret
    return get_scraper_mode() == ScraperMode.FIXTURES  # pragma: allowlist secret


def require_fixtures_mode() -> None:  # pragma: allowlist secret
    if not is_fixtures_mode():  # pragma: allowlist secret
        raise ScraperConfigError(
            f"Expected {SCRAPER_MODE_ENV_VAR}={ScraperMode.FIXTURES.value!r}, "  # pragma: allowlist secret
            f"got {get_scraper_mode().value!r}."
        )


def require_not_fixtures_mode() -> None:
    if is_fixtures_mode():  # pragma: allowlist secret
        raise ScraperConfigError(
            f"Expected {SCRAPER_MODE_ENV_VAR} to be {ScraperMode.LIVE.value!r} or "
            f"{ScraperMode.RECORD.value!r}, got {ScraperMode.FIXTURES.value!r}."
        )
