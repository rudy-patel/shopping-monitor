"""Pytest hooks for integration test environment setup."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from core.settings import clear_settings_cache
from scrapers.contract import ProductSnapshot, ScrapeSource, utc_now
from scrapers.mode import SCRAPER_MODE_ENV_VAR
from scrapers.registry import RetailerEntry, register, reset_registry
from integration_markexpr import markexpr_selects_integration

ROOT = Path(__file__).resolve().parents[2]
SETUP_SCRIPT = ROOT / "scripts" / "setup_integration_env.py"

EXAMPLE_RETAILER_SLUG = "_example_retailer"

_SCRAPER_TEST_FILES = frozenset(
    {
        "test_fixture_convention.py",
        "test_fixture_loader.py",
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
def _scraper_test_registry(request):
    if not _is_scraper_test(request):
        yield
        return
    reset_registry()
    _register_example_retailer()
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


def pytest_configure(config) -> None:
    markexpr = config.getoption("markexpr") or ""
    if not markexpr_selects_integration(markexpr):
        return
    if not SETUP_SCRIPT.exists():
        return
    subprocess.run(
        [sys.executable, str(SETUP_SCRIPT)],
        cwd=ROOT,
        check=False,
    )
