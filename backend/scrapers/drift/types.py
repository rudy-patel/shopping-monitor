"""Pydantic models for retailer drift detection."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from scrapers.benchmark.types import FieldExpect

DriftStatus = Literal["ok", "shape_mismatch", "blocked", "error"]
IssueStatusKind = Literal["shape_mismatch", "blocked", "error"]


class DriftCatalogEntry(BaseModel):
    slug: str
    scenario: str
    url: str
    expect: FieldExpect = Field(default_factory=FieldExpect)
    notes: str | None = None


class DriftSnapshot(BaseModel):
    """Stable structural fingerprint — excludes volatile commerce fields."""

    has_title: bool
    has_price: bool
    has_stock: bool
    has_image: bool
    has_variants: bool
    variant_attribute_names: list[str] = Field(default_factory=list)
    variant_count_bucket: Literal["0", "1", "2+"]
    selected_variant_attribute_names: list[str] = Field(default_factory=list)
    extraction: str | None = None


class DriftCheckResult(BaseModel):
    slug: str
    url: str
    scenario: str
    status: DriftStatus
    message: str | None = None
    diff: dict[str, Any] | None = None
    blocked_markers: list[str] = Field(default_factory=list)
    expect_failures: list[str] = Field(default_factory=list)
    live_fingerprint: DriftSnapshot | None = None
    baseline_fingerprint: DriftSnapshot | None = None


class DriftReport(BaseModel):
    generated_at: datetime
    scraper_mode: str
    catalog_version: str
    dry_run: bool
    file_issues: bool
    results: list[DriftCheckResult]

    @property
    def ok(self) -> bool:
        return all(result.status == "ok" for result in self.results)
