"""Pydantic models for benchmark reports."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

StrategyId = Literal["structured_data", "http_parse", "playwright"]
StrategyStatus = Literal["success", "failed", "skipped", "blocked"]


class FieldExpect(BaseModel):
    title: bool = True
    price: bool = True
    stock: bool = True
    image: bool = True
    variants: bool = False


class CatalogEntry(BaseModel):
    slug: str
    scenario: str
    url: str
    mode: Literal["fixture"] = "fixture"
    expect: FieldExpect = Field(default_factory=FieldExpect)
    notes: str | None = None


class FieldResult(BaseModel):
    ok: bool
    value: Any | None = None
    reason: str | None = None


class StrategyFields(BaseModel):
    title: FieldResult
    price: FieldResult
    stock: FieldResult
    image: FieldResult
    variants: FieldResult


class HttpParseAttempt(BaseModel):
    kind: Literal["html", "retailer_api"]
    status: StrategyStatus
    blocked_markers: list[str] = Field(default_factory=list)
    api: str | None = None
    reason: str | None = None


class StrategyResult(BaseModel):
    strategy: StrategyId
    status: StrategyStatus
    fields: StrategyFields
    runtime_ms: float = 0.0
    retry_count: int = 0
    blocked: bool = False
    blocked_markers: list[str] = Field(default_factory=list)
    http_status: int | None = None
    reason: str | None = None
    http_parse_attempts: list[HttpParseAttempt] = Field(default_factory=list)


class BenchmarkRun(BaseModel):
    slug: str
    scenario: str
    url: str
    expect: FieldExpect
    strategies: list[StrategyResult]


class SlugSummary(BaseModel):
    slug: str
    default_strategy: StrategyId
    fallback_strategies: list[StrategyId] = Field(default_factory=list)
    registry_snippet: str
    notes: str | None = None


class BenchmarkReport(BaseModel):
    generated_at: datetime
    scraper_mode: str
    playwright_available: bool
    catalog_version: str
    runs: list[BenchmarkRun]
    summaries: list[SlugSummary]
