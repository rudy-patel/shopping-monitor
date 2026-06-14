"""Pytest hooks for integration test environment setup."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from _pytest.mark.expression import Expression

from core.settings import clear_settings_cache
from scrapers.contract import ProductSnapshot, ScrapeSource, utc_now
from scrapers.mode import SCRAPER_MODE_ENV_VAR
from scrapers.registry import RetailerEntry, register, reset_registry

ROOT = Path(__file__).resolve().parents[2]
SETUP_SCRIPT = ROOT / "scripts" / "setup_integration_env.py"

EXAMPLE_RETAILER_SLUG = "_example_retailer"

_SCRAPER_TEST_FILES = frozenset(
    {
        "test_bestbuy_ca_scraper.py",
        "test_fixture_convention.py",
        "test_fixture_loader.py",
        "test_generic_scraper.py",
        "test_scraper_contract.py",
        "test_scraper_http_guard.py",
        "test_scraper_mode.py",
        "test_scraper_registry.py",
    }
)


def _is_scraper_test(request: pytest.FixtureRequest) -> bool:
    return request.node.fspath.basename in _SCRAPER_TEST_FILES


def _example_scrape(url: str) -> ProductSnapshot:
    return ProductSnapshot(
        retailer_slug=EXAMPLE_RETAILER_SLUG,
        url=url,
        title="Example Widget",
        current_price_cents=2999,
        currency_seen="CAD",
        is_in_stock=True,
        scraped_at=utc_now(),
        source=ScrapeSource.FIXTURE,
    )


def _register_example_retailer() -> None:
    register(
        RetailerEntry(
            slug=EXAMPLE_RETAILER_SLUG,
            domains=("example-retailer.test",),
            default_category="tech",
            scrape=_example_scrape,
            default_strategy=ScrapeSource.FIXTURE,
        )
    )


@pytest.fixture(autouse=True)
def _block_live_gemini(monkeypatch):
    """Keep pytest/CI off live Gemini; tests mock genai.Client locally when needed."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    clear_settings_cache()
    with patch("services.gemini.genai.Client") as mock_client_cls:
        mock_client_cls.return_value = MagicMock()
        yield
    clear_settings_cache()


@pytest.fixture(autouse=True)
def _scraper_test_registry(request):
    if not _is_scraper_test(request):
        yield
        return
    reset_registry()
    _register_example_retailer()
    if request.node.get_closest_marker("no_generic_registry") is None:
        from scrapers.bestbuy_ca import register_bestbuy_ca
        from scrapers.generic import register_generic

        register_generic()
        register_bestbuy_ca()
    yield
    reset_registry()


@pytest.fixture(autouse=True)
def _isolate_scraper_mode_env(request, monkeypatch):
    if not _is_scraper_test(request):
        yield
        return
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    snapshot = os.environ.get(SCRAPER_MODE_ENV_VAR)
    if snapshot is None:
        monkeypatch.delenv(SCRAPER_MODE_ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(SCRAPER_MODE_ENV_VAR, snapshot)
    clear_settings_cache()
    yield
    clear_settings_cache()


def _markexpr_selects_integration(markexpr: str) -> bool:
    """Return True when pytest's -m filter positively selects integration tests."""
    normalized = markexpr.strip()
    if not normalized:
        return False
    return Expression.compile(normalized).evaluate(lambda name: name == "integration")


def pytest_configure(config) -> None:
    markexpr = config.getoption("markexpr") or ""
    if not _markexpr_selects_integration(markexpr):
        return
    if not SETUP_SCRIPT.exists():
        return
    result = subprocess.run(
        [sys.executable, str(SETUP_SCRIPT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and os.getenv("REQUIRE_INTEGRATION_ENV") == "1":
        message = (result.stderr or result.stdout or "").strip()
        raise pytest.UsageError(
            message or "setup_integration_env.py failed; see make setup-integration-env"
        )
