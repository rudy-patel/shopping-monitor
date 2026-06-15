"""LLM provider interface for discovery, categorization, and search (PRD §5.2 U-ADD-0, §7.3, §7.7, §10.7)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal, Protocol

from pydantic import BaseModel, Field, HttpUrl, field_validator

LlmCategory = Literal["clothing", "shoes", "home", "tech", "other"]


class LlmDiscoveryCandidate(BaseModel):
    url: HttpUrl
    justification: str

    @field_validator("justification")
    @classmethod
    def validate_justification_length(cls, value: str) -> str:
        if len(value) > 280:
            raise ValueError("justification must be at most 280 characters")
        return value


class LlmDiscoveryResult(BaseModel):
    candidates: list[LlmDiscoveryCandidate] = Field(default_factory=list)

    @field_validator("candidates")
    @classmethod
    def validate_candidates_count(
        cls, value: list[LlmDiscoveryCandidate]
    ) -> list[LlmDiscoveryCandidate]:
        if len(value) > 8:
            raise ValueError("candidates must contain at most 8 entries")
        return value


class LlmSearchCandidate(BaseModel):
    """Single search hit returned by the LLM before retailer classification."""

    url: HttpUrl
    title: str = Field(min_length=1, max_length=280)
    retailer_hint: str | None = Field(default=None, max_length=120)
    brand_hint: str | None = Field(default=None, max_length=120)
    justification: str = Field(max_length=200)


class LlmSearchResult(BaseModel):
    candidates: list[LlmSearchCandidate] = Field(default_factory=list)

    @field_validator("candidates")
    @classmethod
    def validate_candidates_count(
        cls, value: list[LlmSearchCandidate]
    ) -> list[LlmSearchCandidate]:
        if len(value) > 8:
            raise ValueError("candidates must contain at most 8 entries")
        return value


class LlmCategorizationResult(BaseModel):
    category: LlmCategory
    raw_response: str | None = None


class LlmProviderError(Exception):
    """Base error for LLM provider failures."""


class LlmTimeoutError(LlmProviderError):
    """LLM request timed out."""


class LlmInvalidResponseError(LlmProviderError):
    """LLM returned an unparseable payload or invalid category slug."""


class LlmQuotaExhaustedError(LlmProviderError):
    """LLM quota exhausted or provider not configured."""


class LlmProvider(Protocol):
    def discover(
        self,
        *,
        title: str,
        brand: str | None,
        retailer_slug: str,
        variant_attributes: Mapping[str, str],
        image_url: str | None,
        reference_price_cents: int | None = None,
    ) -> LlmDiscoveryResult:
        ...

    def categorize(
        self,
        *,
        title: str,
        brand: str | None,
        retailer_slug: str,
        breadcrumbs: Sequence[str],
        timeout_s: float = 1.5,
    ) -> LlmCategorizationResult:
        ...

    def search(self, *, query: str, timeout_s: float = 5.0) -> LlmSearchResult:
        ...


class NoOpLlmProvider:
    """Production-safe default when GEMINI_API_KEY is unset."""

    def discover(
        self,
        *,
        title: str,
        brand: str | None,
        retailer_slug: str,
        variant_attributes: Mapping[str, str],
        image_url: str | None,
        reference_price_cents: int | None = None,
    ) -> LlmDiscoveryResult:
        return LlmDiscoveryResult(candidates=[])

    def categorize(
        self,
        *,
        title: str,
        brand: str | None,
        retailer_slug: str,
        breadcrumbs: Sequence[str],
        timeout_s: float = 1.5,
    ) -> LlmCategorizationResult:
        raise LlmQuotaExhaustedError("LLM provider not configured")

    def search(self, *, query: str, timeout_s: float = 5.0) -> LlmSearchResult:
        raise LlmQuotaExhaustedError("LLM provider not configured")


class FakeLlmProvider:
    """Test double that records calls and returns configured results."""

    def __init__(
        self,
        *,
        discover_result: LlmDiscoveryResult | None = None,
        categorize_result: LlmCategorizationResult | None = None,
        search_result: LlmSearchResult | None = None,
        raise_on_categorize: Exception | None = None,
        raise_on_discover: Exception | None = None,
        raise_on_search: Exception | None = None,
    ) -> None:
        self.discover_result = discover_result or LlmDiscoveryResult(candidates=[])
        self.categorize_result = categorize_result or LlmCategorizationResult(
            category="other"
        )
        self.search_result = search_result or LlmSearchResult(candidates=[])
        self.raise_on_categorize = raise_on_categorize
        self.raise_on_discover = raise_on_discover
        self.raise_on_search = raise_on_search
        self.discover_calls: list[dict] = []
        self.categorize_calls: list[dict] = []
        self.search_calls: list[dict] = []

    def discover(
        self,
        *,
        title: str,
        brand: str | None,
        retailer_slug: str,
        variant_attributes: Mapping[str, str],
        image_url: str | None,
        reference_price_cents: int | None = None,
    ) -> LlmDiscoveryResult:
        self.discover_calls.append(
            {
                "title": title,
                "brand": brand,
                "retailer_slug": retailer_slug,
                "variant_attributes": dict(variant_attributes),
                "image_url": image_url,
                "reference_price_cents": reference_price_cents,
            }
        )
        if self.raise_on_discover is not None:
            raise self.raise_on_discover
        return self.discover_result

    def categorize(
        self,
        *,
        title: str,
        brand: str | None,
        retailer_slug: str,
        breadcrumbs: Sequence[str],
        timeout_s: float = 1.5,
    ) -> LlmCategorizationResult:
        self.categorize_calls.append(
            {
                "title": title,
                "brand": brand,
                "retailer_slug": retailer_slug,
                "breadcrumbs": list(breadcrumbs),
                "timeout_s": timeout_s,
            }
        )
        if self.raise_on_categorize is not None:
            raise self.raise_on_categorize
        return self.categorize_result

    def search(self, *, query: str, timeout_s: float = 5.0) -> LlmSearchResult:
        self.search_calls.append({"query": query, "timeout_s": timeout_s})
        if self.raise_on_search is not None:
            raise self.raise_on_search
        return self.search_result
