"""FixtureLoader read/write tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scrapers.exceptions import FixtureNotFoundError
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret

EXAMPLE_SLUG = "_example_retailer"


@pytest.fixture
def loader() -> FixtureLoader:
    return FixtureLoader()


def test_load_text_happy(loader):
    text = loader.load_text(EXAMPLE_SLUG, "in_stock")
    assert "In Stock" in text


def test_load_bytes_happy(loader):
    data = loader.load_bytes(EXAMPLE_SLUG, "out_of_stock")
    assert b"Out of Stock" in data


def test_load_json_happy(loader):
    payload = loader.load_json(EXAMPLE_SLUG, "api_response")
    assert payload["title"] == "Example Widget"
    assert payload["price_cents"] == 2999


def test_fixture_not_found_includes_absolute_path(loader):
    with pytest.raises(FixtureNotFoundError) as exc_info:
        loader.load_text(EXAMPLE_SLUG, "missing_scenario")
    message = str(exc_info.value)
    assert message.startswith("Fixture not found:")
    assert Path(message.split(": ", 1)[1]).is_absolute()


def test_record_writes_new_fixture(tmp_path):
    loader = FixtureLoader(root=tmp_path)
    path = loader.record(EXAMPLE_SLUG, "new_scenario", "<html></html>")
    assert path.exists()
    assert path.read_text(encoding="utf-8") == "<html></html>"


def test_record_refuses_overwrite(tmp_path):
    loader = FixtureLoader(root=tmp_path)
    loader.record(EXAMPLE_SLUG, "dup", "first")
    with pytest.raises(FileExistsError):
        loader.record(EXAMPLE_SLUG, "dup", "second")


def test_record_overwrite_when_requested(tmp_path):
    loader = FixtureLoader(root=tmp_path)
    loader.record(EXAMPLE_SLUG, "dup", "first")
    loader.record(EXAMPLE_SLUG, "dup", "second", overwrite=True)
    assert loader.load_text(EXAMPLE_SLUG, "dup") == "second"


def test_record_atomic_write_cleanup_on_failure(tmp_path, monkeypatch):
    loader = FixtureLoader(root=tmp_path)

    def fail_replace(src, dst):
        raise OSError("simulated failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated failure"):
        loader.record(EXAMPLE_SLUG, "atomic_fail", "content")
    tmp_file = tmp_path / EXAMPLE_SLUG / "atomic_fail.html.tmp"
    assert not tmp_file.exists()


def test_record_creates_retailer_subdirectory(tmp_path):
    loader = FixtureLoader(root=tmp_path)
    loader.record("brand_new_retailer", "in_stock", "<html></html>")
    assert (tmp_path / "brand_new_retailer" / "in_stock.html").is_file()


@pytest.mark.parametrize("bad_name", ["In_Stock", "with-dash", "trailing "])
def test_bad_scenario_names_raise(loader, bad_name):
    with pytest.raises(ValueError, match="scenario name"):
        loader.path(EXAMPLE_SLUG, bad_name)


def test_iter_scenarios(loader):
    scenarios = set(loader.iter_scenarios(EXAMPLE_SLUG))
    assert ("in_stock", "html") in scenarios
    assert ("out_of_stock", "html") in scenarios
    assert ("multi_variant", "html") in scenarios
    assert ("api_response", "json") in scenarios


def test_required_scenarios_example_retailer(loader):
    assert loader.required_scenarios(EXAMPLE_SLUG) == {
        "in_stock",
        "out_of_stock",
        "multi_variant",
    }


def test_required_scenarios_generic(loader):
    assert loader.required_scenarios("generic") == {
        "in_stock",
        "out_of_stock",
        "multi_variant",
        "jsonld_friendly",
        "og_only",
        "no_extractable_data",
    }
