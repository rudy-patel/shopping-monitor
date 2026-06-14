"""Internal types for structured-data extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scrapers.contract import VariantAttribute, VariantCombination


@dataclass
class ExtractedFields:
    title: str | None = None
    brand: str | None = None
    image_url: str | None = None
    price_cents: int | None = None
    currency: str | None = None
    is_in_stock: bool | None = None
    available_variants: list[VariantCombination] = field(default_factory=list)
    selected_variant: list[VariantAttribute] | None = None
    breadcrumbs: list[str] = field(default_factory=list)
    raw_snapshot: dict[str, Any] = field(default_factory=dict)
