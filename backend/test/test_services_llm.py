"""LlmProvider interface tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from services.llm import (
    FakeLlmProvider,
    LlmCategorizationResult,
    LlmDiscoveryCandidate,
    LlmDiscoveryResult,
    LlmInvalidResponseError,
    LlmQuotaExhaustedError,
    LlmTimeoutError,
    NoOpLlmProvider,
)


def test_noop_discover_returns_empty_candidates():
    provider = NoOpLlmProvider()
    result = provider.discover(
        title="Test",
        brand=None,
        retailer_slug="bestbuy_ca",
        variant_attributes={},
        image_url=None,
    )
    assert result == LlmDiscoveryResult(candidates=[])


def test_noop_categorize_raises_quota_exhausted():
    provider = NoOpLlmProvider()
    with pytest.raises(LlmQuotaExhaustedError, match="not configured"):
        provider.categorize(
            title="Test",
            brand=None,
            retailer_slug="bestbuy_ca",
            breadcrumbs=[],
        )


def test_fake_returns_configured_results():
    discover = LlmDiscoveryResult(
        candidates=[
            LlmDiscoveryCandidate(
                url="https://example.com/p",
                justification="match",
            )
        ]
    )
    categorize = LlmCategorizationResult(category="tech")
    provider = FakeLlmProvider(
        discover_result=discover,
        categorize_result=categorize,
    )
    assert provider.discover(
        title="T",
        brand=None,
        retailer_slug="x",
        variant_attributes={},
        image_url=None,
    ) == discover
    assert provider.categorize(
        title="T",
        brand=None,
        retailer_slug="x",
        breadcrumbs=[],
    ) == categorize


def test_fake_raises_configured_exceptions():
    provider = FakeLlmProvider(
        raise_on_discover=LlmTimeoutError("timeout"),
        raise_on_categorize=LlmInvalidResponseError("bad"),
    )
    with pytest.raises(LlmTimeoutError):
        provider.discover(
            title="T",
            brand=None,
            retailer_slug="x",
            variant_attributes={},
            image_url=None,
        )
    with pytest.raises(LlmInvalidResponseError):
        provider.categorize(
            title="T",
            brand=None,
            retailer_slug="x",
            breadcrumbs=[],
        )


def test_fake_records_call_args():
    provider = FakeLlmProvider()
    provider.discover(
        title="Title",
        brand="Brand",
        retailer_slug="slug",
        variant_attributes={"color": "red"},
        image_url="https://img.example/x.jpg",
    )
    provider.categorize(
        title="Title",
        brand="Brand",
        retailer_slug="slug",
        breadcrumbs=["A", "B"],
        timeout_s=2.0,
    )
    assert provider.discover_calls == [
        {
            "title": "Title",
            "brand": "Brand",
            "retailer_slug": "slug",
            "variant_attributes": {"color": "red"},
            "image_url": "https://img.example/x.jpg",
        }
    ]
    assert provider.categorize_calls == [
        {
            "title": "Title",
            "brand": "Brand",
            "retailer_slug": "slug",
            "breadcrumbs": ["A", "B"],
            "timeout_s": 2.0,
        }
    ]


def test_discovery_result_rejects_more_than_8_candidates():
    candidates = [
        LlmDiscoveryCandidate(
            url=f"https://example.com/{i}",
            justification=f"reason {i}",
        )
        for i in range(9)
    ]
    with pytest.raises(ValidationError, match="candidates"):
        LlmDiscoveryResult(candidates=candidates)


def test_categorization_result_rejects_invalid_category():
    with pytest.raises(ValidationError):
        LlmCategorizationResult.model_validate({"category": "invalid_slug"})


def test_discovery_candidate_rejects_long_justification():
    with pytest.raises(ValidationError, match="justification"):
        LlmDiscoveryCandidate(
            url="https://example.com/p",
            justification="x" * 281,
        )
