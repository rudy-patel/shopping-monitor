"""Categorizer interface tests."""

from __future__ import annotations

import pytest

from services.categorizer import (
    CategorizationContext,
    DefaultCategorizer,
    heuristic_category,
)
from services.llm import (
    FakeLlmProvider,
    LlmCategorizationResult,
    LlmInvalidResponseError,
    LlmQuotaExhaustedError,
    LlmTimeoutError,
)


def test_manual_override_short_circuits():
    llm = FakeLlmProvider()
    categorizer = DefaultCategorizer(llm)
    result = categorizer.categorize(
        CategorizationContext(
            title="Anything",
            retailer_slug="unknown",
            manual_override="shoes",
        )
    )
    assert result.category == "shoes"
    assert result.source == "manual"
    assert llm.categorize_calls == []


def test_llm_happy_path():
    llm = FakeLlmProvider(
        categorize_result=LlmCategorizationResult(category="tech"),
    )
    result = DefaultCategorizer(llm).categorize(
        CategorizationContext(title="Laptop", retailer_slug="bestbuy_ca")
    )
    assert (result.category, result.source) == ("tech", "llm")


def test_llm_timeout_falls_through_to_heuristic():
    llm = FakeLlmProvider(raise_on_categorize=LlmTimeoutError("timeout"))
    result = DefaultCategorizer(llm).categorize(
        CategorizationContext(
            title="Generic item",
            retailer_slug="unknown",
            breadcrumbs=["Electronics", "Laptops"],
        )
    )
    assert result.category == "tech"
    assert result.source == "heuristic"


def test_llm_invalid_response_falls_through_to_heuristic():
    llm = FakeLlmProvider(raise_on_categorize=LlmInvalidResponseError("bad"))
    result = DefaultCategorizer(llm).categorize(
        CategorizationContext(
            title="Generic item",
            retailer_slug="unknown",
            breadcrumbs=["Electronics", "Laptops"],
        )
    )
    assert result.category == "tech"
    assert result.source == "heuristic"


def test_llm_quota_exhausted_falls_through_to_heuristic():
    llm = FakeLlmProvider(raise_on_categorize=LlmQuotaExhaustedError("quota"))
    result = DefaultCategorizer(llm).categorize(
        CategorizationContext(
            title="Generic item",
            retailer_slug="unknown",
            breadcrumbs=["Electronics", "Laptops"],
        )
    )
    assert result.category == "tech"
    assert result.source == "heuristic"


def test_heuristic_no_match_defaults_to_other():
    llm = FakeLlmProvider(raise_on_categorize=LlmQuotaExhaustedError("quota"))
    result = DefaultCategorizer(llm).categorize(
        CategorizationContext(
            title="Mystery widget",
            retailer_slug="unknown_retailer",
        )
    )
    assert result.category == "other"
    assert result.source == "default_other"


def test_heuristic_precedence_breadcrumb_beats_title():
    category = heuristic_category(
        title="sneaker boots runner",
        brand=None,
        retailer_slug="bestbuy_ca",
        breadcrumbs=["Electronics", "Laptops"],
        retailer_defaults={"bestbuy_ca": "tech"},
    )
    assert category == "tech"


def test_heuristic_precedence_title_beats_retailer_default():
    category = heuristic_category(
        title="Running sneaker",
        brand=None,
        retailer_slug="bestbuy_ca",
        breadcrumbs=[],
        retailer_defaults={"bestbuy_ca": "tech"},
    )
    assert category == "shoes"


def test_heuristic_precedence_retailer_default_beats_none():
    category = heuristic_category(
        title="Mystery widget",
        brand=None,
        retailer_slug="bestbuy_ca",
        breadcrumbs=[],
        retailer_defaults={"bestbuy_ca": "tech"},
    )
    assert category == "tech"


def test_heuristic_category_callable_independently():
    assert (
        heuristic_category(
            title="x",
            brand=None,
            retailer_slug="y",
            breadcrumbs=["Kitchen"],
            retailer_defaults={},
        )
        == "home"
    )
    assert (
        heuristic_category(
            title="x",
            brand=None,
            retailer_slug="y",
            breadcrumbs=[],
            retailer_defaults={},
        )
        is None
    )


def test_categorizer_does_not_swallow_unexpected_exceptions():
    llm = FakeLlmProvider(raise_on_categorize=RuntimeError("unexpected"))
    categorizer = DefaultCategorizer(llm)
    with pytest.raises(RuntimeError, match="unexpected"):
        categorizer.categorize(
            CategorizationContext(title="Test", retailer_slug="x")
        )
