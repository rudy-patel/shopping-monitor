"""Tests for Shopify theme meta variant extraction."""

from __future__ import annotations

from scrapers.extraction.shopify import (
    extract_shopify_meta,
    merge_shopify_extraction,
    variant_id_from_url,
)

_PALMISLE_MULTI_META = """
<script>
var meta = {"product":{"id":1,"variants":[
  {"id":111,"price":4800,"name":"Tee - Green - S","public_title":"S","sku":"SKU-S"},
  {"id":222,"price":4800,"name":"Tee - Green - M","public_title":"M","sku":"SKU-M"}
]}};
</script>
"""

_PALMISLE_JSONLD = """
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product",
 "name":"American Rapture Tee","brand":{"@type":"Brand","name":"Violet"},
 "image":"https://cdn.example/tee.png",
 "offers":{"@type":"Offer","price":"48.00","priceCurrency":"CAD",
           "availability":"https://schema.org/InStock"}}
</script></head></html>
"""

_COLOR_SIZE_META = """
<script>
var meta = {"product":{"variants":[
  {"id":9001,"price":3200,"name":"Shirt - black / S","public_title":"black / S","sku":"SH-S"}
]}};
</script>
"""


def test_variant_id_from_url():
    assert variant_id_from_url("https://shop.test/p?variant=50681068192033") == "50681068192033"
    assert variant_id_from_url("https://shop.test/p") is None


def test_extract_shopify_meta_builds_size_variants():
    extracted = extract_shopify_meta(_PALMISLE_MULTI_META, url="https://shop.test/p")
    assert len(extracted.available_variants) == 2
    assert extracted.available_variants[0].attributes[0].attribute_name == "size"
    assert extracted.available_variants[0].attributes[0].attribute_value == "S"
    assert extracted.available_variants[0].sku == "SKU-S"


def test_extract_shopify_meta_selected_variant_from_url():
    url = "https://shop.test/p?variant=222"
    extracted = extract_shopify_meta(_PALMISLE_MULTI_META, url=url)
    assert extracted.selected_variant is not None
    assert extracted.selected_variant[0].attribute_value == "M"


def test_extract_shopify_meta_color_size_public_title():
    extracted = extract_shopify_meta(_COLOR_SIZE_META, url="https://shop.test/p")
    attrs = extracted.available_variants[0].attributes
    assert [(a.attribute_name, a.attribute_value) for a in attrs] == [
        ("color", "black"),
        ("size", "S"),
    ]


def test_merge_shopify_extraction_combines_jsonld_and_meta():
    html = _PALMISLE_JSONLD.replace("</head>", _PALMISLE_MULTI_META + "</head>")
    extracted = merge_shopify_extraction(
        html,
        url="https://shop.test/p?variant=111",
    )
    assert extracted.title == "American Rapture Tee"
    assert extracted.price_cents == 4800
    assert extracted.currency == "CAD"
    assert len(extracted.available_variants) == 2
    assert extracted.selected_variant is not None
    assert extracted.selected_variant[0].attribute_value == "S"


def test_merge_shopify_extraction_palmisle_recorded_fixture():
    from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret

    html = FixtureLoader().load_text("palmisleskate", "multi_variant")
    extracted = merge_shopify_extraction(
        html,
        url="https://fixtures.local/palmisleskate/multi_variant",
    )
    assert extracted.title is not None
    assert extracted.price_cents == 4800
    assert len(extracted.available_variants) >= 2
