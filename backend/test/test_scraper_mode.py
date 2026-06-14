"""Scraper mode resolution tests."""

from __future__ import annotations

import pytest

from core.settings import DEFAULT_SCRAPER_MODE, clear_settings_cache
from scrapers.exceptions import ScraperConfigError
from scrapers.mode import (
    SCRAPER_MODE_ENV_VAR,
    ScraperMode,
    get_scraper_mode,
    require_fixtures_mode,  # pragma: allowlist secret
)


@pytest.fixture(autouse=True)
def _clear_settings_between_mode_tests(monkeypatch):
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_default_mode_is_fixture_mode(monkeypatch):
    monkeypatch.delenv(SCRAPER_MODE_ENV_VAR, raising=False)
    clear_settings_cache()
    assert get_scraper_mode().value == DEFAULT_SCRAPER_MODE  # fixture mode


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (DEFAULT_SCRAPER_MODE, ScraperMode.FIXTURES),  # pragma: allowlist secret
        ("live", ScraperMode.LIVE),
        ("record", ScraperMode.RECORD),
    ],
)
def test_explicit_modes_parse(monkeypatch, raw, expected):
    monkeypatch.setenv(SCRAPER_MODE_ENV_VAR, raw)
    clear_settings_cache()
    assert get_scraper_mode() == expected


@pytest.mark.parametrize("raw", ["FIXTURES", "  live  ", "Record", "garbage"])  # pragma: allowlist secret
def test_non_canonical_mode_values_raise(monkeypatch, raw):
    monkeypatch.setenv(SCRAPER_MODE_ENV_VAR, raw)
    clear_settings_cache()
    with pytest.raises(ScraperConfigError):
        get_scraper_mode()


def test_require_fixture_mode_guard_passes_in_default_mode(monkeypatch):
    monkeypatch.delenv(SCRAPER_MODE_ENV_VAR, raising=False)
    clear_settings_cache()
    require_fixtures_mode()  # pragma: allowlist secret


def test_require_fixture_mode_guard_raises_in_live_mode(monkeypatch):
    monkeypatch.setenv(SCRAPER_MODE_ENV_VAR, "live")
    clear_settings_cache()

    with pytest.raises(ScraperConfigError, match="Expected"):
        require_fixtures_mode()  # pragma: allowlist secret


def test_automated_tests_require_fixture_mode():
    """CI and local unit tests must resolve to fixture mode (explicit or default)."""
    clear_settings_cache()
    require_fixtures_mode()  # pragma: allowlist secret
