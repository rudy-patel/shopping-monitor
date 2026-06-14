"""Pydantic contract for retailer scrape results."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

_RETAILER_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_RAW_SNAPSHOT_MAX_BYTES = 32 * 1024


class VariantAttribute(BaseModel):
    attribute_name: str
    attribute_value: str


class VariantCombination(BaseModel):
    attributes: list[VariantAttribute]
    sku: str | None = None
    is_in_stock: bool | None = None


class ScrapeSource(str, Enum):
    STRUCTURED_DATA = "structured_data"
    HTTP_PARSE = "http_parse"
    PLAYWRIGHT = "playwright"
    FIXTURE = "fixture"


class ProductSnapshot(BaseModel):
    retailer_slug: str
    url: HttpUrl
    title: str
    brand: str | None = None
    image_url: HttpUrl | None = None
    current_price_cents: int
    currency_seen: str
    is_in_stock: bool
    available_variants: list[VariantCombination] = Field(default_factory=list)
    selected_variant: list[VariantAttribute] | None = None
    breadcrumbs: list[str] = Field(default_factory=list)
    scraped_at: datetime
    source: ScrapeSource
    raw_snapshot: dict[str, Any] = Field(default_factory=dict)

    @field_validator("current_price_cents")
    @classmethod
    def validate_price_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("current_price_cents must be >= 0")
        return value

    @field_validator("currency_seen")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        if len(value) != 3 or not value.isascii() or not value.isupper():
            raise ValueError(
                "currency_seen must be a 3-character upper-case ISO 4217 code"
            )
        return value

    @field_validator("scraped_at")
    @classmethod
    def validate_scraped_at_tz_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("scraped_at must be timezone-aware")
        return value

    @field_validator("retailer_slug")
    @classmethod
    def validate_retailer_slug(cls, value: str) -> str:
        if not _RETAILER_SLUG_RE.match(value):
            raise ValueError(
                "retailer_slug must be snake_case matching [a-z][a-z0-9_]*"
            )
        return value

    @model_validator(mode="after")
    def validate_raw_snapshot_size(self) -> ProductSnapshot:
        serialized = json.dumps(self.raw_snapshot, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > _RAW_SNAPSHOT_MAX_BYTES:
            raise ValueError(
                f"raw_snapshot serialized size exceeds {_RAW_SNAPSHOT_MAX_BYTES} bytes"
            )
        return self


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)
