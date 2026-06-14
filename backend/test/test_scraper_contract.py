"""ProductSnapshot contract validation tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from scrapers.contract import (
    ProductSnapshot,
    ScrapeSource,
    VariantAttribute,
    VariantCombination,
)

_VALID_SNAPSHOT = {
    "retailer_slug": "bestbuy_ca",
    "url": "https://www.bestbuy.ca/en-ca/product/foo",
    "title": "Example Product",
    "brand": "ExampleBrand",
    "current_price_cents": 1999,
    "currency_seen": "CAD",
    "is_in_stock": True,
    "scraped_at": datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc),
    "source": ScrapeSource.FIXTURE,
}


def test_product_snapshot_round_trip():
    snapshot = ProductSnapshot.model_validate(_VALID_SNAPSHOT)
    restored = ProductSnapshot.model_validate(snapshot.model_dump())
    assert restored == snapshot


def test_negative_price_rejected():
    data = {**_VALID_SNAPSHOT, "current_price_cents": -1}
    with pytest.raises(ValidationError, match="current_price_cents"):
        ProductSnapshot.model_validate(data)


def test_lowercase_currency_rejected():
    data = {**_VALID_SNAPSHOT, "currency_seen": "cad"}
    with pytest.raises(ValidationError, match="currency_seen"):
        ProductSnapshot.model_validate(data)


def test_naive_scraped_at_rejected():
    data = {**_VALID_SNAPSHOT, "scraped_at": datetime(2026, 6, 14, 12, 0, 0)}
    with pytest.raises(ValidationError, match="scraped_at"):
        ProductSnapshot.model_validate(data)


def test_raw_snapshot_small_accepted():
    data = {**_VALID_SNAPSHOT, "raw_snapshot": {"key": "value"}}
    snapshot = ProductSnapshot.model_validate(data)
    assert snapshot.raw_snapshot == {"key": "value"}


def test_raw_snapshot_over_cap_rejected():
    big_value = "x" * (32 * 1024)
    data = {**_VALID_SNAPSHOT, "raw_snapshot": {"payload": big_value}}
    with pytest.raises(ValidationError, match="raw_snapshot"):
        ProductSnapshot.model_validate(data)


def test_variant_attribute_happy():
    attr = VariantAttribute(attribute_name="Color", attribute_value="Red")
    assert attr.attribute_name == "Color"
    assert attr.attribute_value == "Red"


def test_variant_combination_happy():
    combo = VariantCombination(
        attributes=[VariantAttribute(attribute_name="Size", attribute_value="M")],
        sku="SKU-123",
        is_in_stock=True,
    )
    assert combo.sku == "SKU-123"
    assert combo.is_in_stock is True


def test_variant_combination_bad_shape():
    with pytest.raises(ValidationError):
        VariantCombination.model_validate({"attributes": "not-a-list"})


def test_retailer_slug_regex_enforced():
    data = {**_VALID_SNAPSHOT, "retailer_slug": "BestBuy_CA"}
    with pytest.raises(ValidationError, match="retailer_slug"):
        ProductSnapshot.model_validate(data)
