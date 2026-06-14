"""Fixture naming convention enforcement."""

from __future__ import annotations

from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret
from scrapers.registry import all_retailers


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
