"""Tests for FixtureLlmProvider (T8.10)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.llm_fixtures import FixtureLlmProvider, slugify_query


def test_slugify_lowercases_and_dashes():
    assert slugify_query("Nintendo Switch 2") == "nintendo-switch-2"
    assert slugify_query("  AirPods   Pro  ") == "airpods-pro"


def test_search_returns_canned_results_for_known_query():
    provider = FixtureLlmProvider()
    result = provider.search(query="Nintendo Switch 2")
    assert len(result.candidates) >= 1
    assert any(
        str(c.url).startswith("https://fixtures.local/bestbuy_ca/")
        for c in result.candidates
    )


def test_search_returns_canned_results_for_patagonia_short_query():
    provider = FixtureLlmProvider()
    result = provider.search(query="patagonia")
    assert len(result.candidates) >= 1


@pytest.mark.parametrize(
    "query",
    ["AirPods Pro", "Nintendo Switch 2", "Lenovo Yoga laptop", "Patagonia jacket"],
)
def test_all_example_query_chips_have_fixtures(query: str):
    """Every example chip shown in SearchCommandDialog must resolve to a fixture
    so fixture-mode dev/demo doesn't dead-end on empty results."""
    provider = FixtureLlmProvider()
    result = provider.search(query=query)
    assert len(result.candidates) >= 1, f"missing fixture for example chip {query!r}"


def test_search_returns_empty_for_unknown_query():
    provider = FixtureLlmProvider()
    result = provider.search(query="completely unknown query xyz")
    assert result.candidates == []


def test_search_returns_empty_for_blank_query():
    provider = FixtureLlmProvider()
    assert provider.search(query="").candidates == []


def test_search_reads_custom_fixture_dir(tmp_path: Path):
    fixture = tmp_path / "custom-query.json"
    fixture.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "url": "https://www.indigo.ca/en-ca/p/x",
                        "title": "Custom Title",
                        "retailer_hint": "Indigo",
                        "brand_hint": None,
                        "justification": "matches",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    provider = FixtureLlmProvider(fixture_dir=tmp_path)
    result = provider.search(query="custom query")
    assert len(result.candidates) == 1
    assert result.candidates[0].title == "Custom Title"


def test_categorize_deterministic_heuristic_for_obvious_queries():
    provider = FixtureLlmProvider()
    assert (
        provider.categorize(
            title="Sony WH-1000XM5 Headphones",
            brand="Sony",
            retailer_slug="bestbuy_ca",
            breadcrumbs=[],
        ).category
        == "tech"
    )
    assert (
        provider.categorize(
            title="Nike Running Shoes",
            brand="Nike",
            retailer_slug="nike_ca",
            breadcrumbs=[],
        ).category
        == "shoes"
    )


def test_categorize_falls_back_to_other_for_unknown():
    provider = FixtureLlmProvider()
    assert (
        provider.categorize(
            title="Mystery item",
            brand=None,
            retailer_slug="generic",
            breadcrumbs=[],
        ).category
        == "other"
    )


def test_discover_returns_empty_in_fixture_mode():
    provider = FixtureLlmProvider()
    result = provider.discover(
        title="x",
        brand=None,
        retailer_slug="bestbuy_ca",
        variant_attributes={},
        image_url=None,
    )
    assert result.candidates == []


def test_fixture_dir_raises_on_invalid_json(tmp_path: Path):
    bad = tmp_path / "bad-query.json"
    bad.write_text("not json", encoding="utf-8")
    provider = FixtureLlmProvider(fixture_dir=tmp_path)
    with pytest.raises(Exception):  # noqa: B017 — LlmInvalidResponseError
        provider.search(query="bad query")
