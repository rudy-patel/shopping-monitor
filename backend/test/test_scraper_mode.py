"""Scraper mode resolution tests."""

from __future__ import annotations

import os

import pytest

from core.settings import DEFAULT_SCRAPER_MODE
from scrapers.exceptions import ScraperConfigError
from scrapers.mode import SCRAPER_MODE_ENV_VAR, ScraperMode, get_scraper_mode


def test_default_mode_is_fixture_mode(monkeypatch):
    monkeypatch.delenv(SCRAPER_MODE_ENV_VAR, raising=False)
    assert get_scraper_mode().value == DEFAULT_SCRAPER_MODE


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (DEFAULT_SCRAPER_MODE, ScraperMode.FIXTURES),  # pragma: allowlist secret
        ("FIXTURES", ScraperMode.FIXTURES),  # pragma: allowlist secret
        ("  live  ", ScraperMode.LIVE),
        ("Record", ScraperMode.RECORD),
    ],
)
def test_explicit_modes_parse(monkeypatch, raw, expected):
    monkeypatch.setenv(SCRAPER_MODE_ENV_VAR, raw)
    assert get_scraper_mode() == expected


def test_garbage_mode_raises(monkeypatch):
    monkeypatch.setenv(SCRAPER_MODE_ENV_VAR, "garbage")
    with pytest.raises(ScraperConfigError, match="Invalid"):
        get_scraper_mode()


def test_ci_default_is_fixture_mode():
    """Without env override, resolved mode must be fixture mode for CI safety."""
    env_value = os.environ.get(SCRAPER_MODE_ENV_VAR)
    if env_value is not None:
        pytest.skip("scraper mode env var is set in the environment")
    assert get_scraper_mode().value == DEFAULT_SCRAPER_MODE
