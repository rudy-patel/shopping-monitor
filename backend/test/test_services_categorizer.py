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


@pytest.mark.parametrize(
    "llm_error",
    [
        LlmTimeoutError("timeout"),
        LlmInvalidResponseError("bad"),
        LlmQuotaExhaustedError("quota"),
    ],
)
def test_llm_provider_errors_fall_through_to_heuristic(llm_error: Exception):
    llm = FakeLlmProvider(raise_on_categorize=llm_error)
    result = DefaultCategorizer(llm).categorize(
        CategorizationContext(
            title="Generic item",
            retailer_slug="unknown",
            breadcrumbs=["Electronics", "Laptops"],
        )
    )
    assert result.category == "tech"
    assert result.source == "heuristic"


def test_default_categorizer_uses_retailer_default_via_heuristic():
    llm = FakeLlmProvider(raise_on_categorize=LlmQuotaExhaustedError("quota"))
    categorizer = DefaultCategorizer(
        llm,
        retailer_defaults={"bestbuy_ca": "tech"},
    )
    result = categorizer.categorize(
        CategorizationContext(title="Mystery widget", retailer_slug="bestbuy_ca")
    )
    assert result.category == "tech"
    assert result.source == "heuristic"


def test_heuristic_ignores_invalid_retailer_default():
    category = heuristic_category(
        title="Mystery widget",
        brand=None,
        retailer_slug="bestbuy_ca",
        breadcrumbs=[],
        retailer_defaults={"bestbuy_ca": "not_a_real_category"},
    )
    assert category is None


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


def test_heuristic_precedence_retailer_default_beats_breadcrumb():
    category = heuristic_category(
        title="sneaker boots runner",
        brand=None,
        retailer_slug="bestbuy_ca",
        breadcrumbs=["Home", "Kitchen"],
        retailer_defaults={"bestbuy_ca": "tech"},
    )
    assert category == "tech"


def test_heuristic_precedence_breadcrumb_beats_title_without_retailer_default():
    category = heuristic_category(
        title="Running sneaker",
        brand=None,
        retailer_slug="unknown_retailer",
        breadcrumbs=["Electronics", "Laptops"],
        retailer_defaults={},
    )
    assert category == "tech"


def test_heuristic_precedence_retailer_default_beats_title():
    category = heuristic_category(
        title="Running sneaker",
        brand=None,
        retailer_slug="bestbuy_ca",
        breadcrumbs=[],
        retailer_defaults={"bestbuy_ca": "tech"},
    )
    assert category == "tech"


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
