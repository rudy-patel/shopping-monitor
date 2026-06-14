"""Product categorization orchestrator (PRD §7.7)."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Literal, Protocol

from pydantic import BaseModel

from services.llm import (
    LlmCategory,
    LlmProvider,
    LlmProviderError,
)

CategorySource = Literal["manual", "llm", "heuristic", "default_other"]

_BREADCRUMB_KEYWORDS: dict[str, tuple[str, ...]] = {
    "clothing": (
        "clothing",
        "apparel",
        "tops",
        "bottoms",
        "outerwear",
        "jacket",
        "shirt",
        "pants",
    ),
    "shoes": ("shoes", "footwear", "sneakers", "boots", "skate shoes"),
    "home": (
        "home",
        "kitchen",
        "furniture",
        "decor",
        "appliances",
        "bedding",
    ),
    "tech": (
        "tech",
        "electronics",
        "computers",
        "laptops",
        "phones",
        "audio",
        "tv",
        "gaming",
    ),
}

_TITLE_BRAND_KEYWORDS: dict[str, tuple[str, ...]] = {
    "shoes": ("shoe", "sneaker", "boot", "runner"),
    "tech": ("laptop", "tablet", "headphone", "monitor", "router", "console"),
    "clothing": ("t-shirt", "hoodie", "jacket", "jeans"),
    "home": ("kettle", "mattress", "lamp", "blender"),
}


class CategorizationContext(BaseModel):
    title: str
    brand: str | None = None
    retailer_slug: str
    breadcrumbs: list[str] = []
    manual_override: LlmCategory | None = None


class CategorizationResult(BaseModel):
    category: LlmCategory
    source: CategorySource


class Categorizer(Protocol):
    def categorize(self, ctx: CategorizationContext) -> CategorizationResult:
        ...


def _breadcrumb_matches(breadcrumb_text: str, keyword: str) -> bool:
    lowered = breadcrumb_text.lower()
    if " " in keyword:
        return keyword in lowered
    tokens = re.findall(r"[a-z0-9]+", lowered)
    return keyword in tokens


def heuristic_category(
    *,
    title: str,
    brand: str | None,
    retailer_slug: str,
    breadcrumbs: list[str],
    retailer_defaults: Mapping[str, str],
) -> LlmCategory | None:
    """Return a category from breadcrumbs, title/brand keywords, or retailer default."""
    breadcrumb_text = " ".join(breadcrumbs).lower()
    for category, keywords in _BREADCRUMB_KEYWORDS.items():
        if any(_breadcrumb_matches(breadcrumb_text, keyword) for keyword in keywords):
            return category  # type: ignore[return-value]

    title_brand_text = f"{title} {brand or ''}".lower()
    for category, keywords in _TITLE_BRAND_KEYWORDS.items():
        if any(keyword in title_brand_text for keyword in keywords):
            return category  # type: ignore[return-value]

    default = retailer_defaults.get(retailer_slug)
    if default is not None:
        return default  # type: ignore[return-value]

    return None


class DefaultCategorizer:
    """Orchestrates manual → LLM → heuristic → default_other categorization."""

    def __init__(
        self,
        llm: LlmProvider,
        *,
        retailer_defaults: Mapping[str, str] | None = None,
    ) -> None:
        self._llm = llm
        self._retailer_defaults = retailer_defaults or {}

    def categorize(self, ctx: CategorizationContext) -> CategorizationResult:
        if ctx.manual_override is not None:
            return CategorizationResult(
                category=ctx.manual_override,
                source="manual",
            )

        try:
            llm_result = self._llm.categorize(
                title=ctx.title,
                brand=ctx.brand,
                retailer_slug=ctx.retailer_slug,
                breadcrumbs=ctx.breadcrumbs,
            )
            return CategorizationResult(
                category=llm_result.category,
                source="llm",
            )
        except LlmProviderError:
            pass

        heuristic = heuristic_category(
            title=ctx.title,
            brand=ctx.brand,
            retailer_slug=ctx.retailer_slug,
            breadcrumbs=ctx.breadcrumbs,
            retailer_defaults=self._retailer_defaults,
        )
        if heuristic is not None:
            return CategorizationResult(category=heuristic, source="heuristic")

        return CategorizationResult(category="other", source="default_other")
