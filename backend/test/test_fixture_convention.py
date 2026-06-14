"""Fixture naming convention enforcement."""

from __future__ import annotations

from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret
from scrapers.registry import all_retailers, reset_registry


def _register_production_retailers() -> None:
    from scrapers.abercrombie import register_abercrombie
    from scrapers.apple_ca import register_apple_ca
    from scrapers.bestbuy_ca import register_bestbuy_ca
    from scrapers.generic import register_generic
    from scrapers.indigo import register_indigo
    from scrapers.palmisleskate import register_palmisleskate
    from scrapers.tikiroomskate import register_tikiroomskate

    register_generic()
    register_bestbuy_ca()
    register_palmisleskate()
    register_tikiroomskate()
    register_indigo()
    register_apple_ca()
    register_abercrombie()


def test_registered_retailers_have_required_fixture_files():
    loader = FixtureLoader()
    for entry in all_retailers():
        fixture_slug = entry.fixture_dir or entry.slug
        required = loader.required_scenarios(entry.slug)
        for scenario in required:
            assert loader.exists(fixture_slug, scenario, ext="html"), (
                f"Missing fixture: {fixture_slug}/{scenario}.html "
                f"for retailer {entry.slug!r}"
            )


def test_production_retailers_have_required_fixture_files():
    reset_registry()
    _register_production_retailers()
    loader = FixtureLoader()
    for entry in all_retailers():
        if entry.slug == "generic":
            continue
        fixture_slug = entry.fixture_dir or entry.slug
        for scenario in loader.required_scenarios(entry.slug):
            assert loader.exists(fixture_slug, scenario, ext="html"), (
                f"Missing fixture: {fixture_slug}/{scenario}.html "
                f"for retailer {entry.slug!r}"
            )
