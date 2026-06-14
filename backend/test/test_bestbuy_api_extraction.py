"""Tests for Best Buy JSON API extraction fallback."""

from __future__ import annotations

import pytest

from scrapers.bestbuy_ca import extract_bestbuy_html
from scrapers.extraction.bestbuy_api import (
    extract_bestbuy_api_json,
    json_api_to_fixture_html,
)
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret

_SWITCH_2_PAYLOAD = {
    "name": "Nintendo Switch 2 Console",
    "sku": "19296507",
    "brandName": "NINTENDO",
    "salePrice": 629.99,
    "regularPrice": 629.99,
    "categoryName": "Nintendo Switch 2 Consoles",
    "thumbnailImage": "https://multimedia.bbycastatic.ca/multimedia/products/55x55/192/19296/19296507.jpg",
    "availability": {
        "onlineAvailability": "InStock",
        "isAvailableOnline": True,
    },
}


def test_extract_bestbuy_api_json_switch_2():
    extracted = extract_bestbuy_api_json(_SWITCH_2_PAYLOAD)
    assert extracted.title == "Nintendo Switch 2 Console"
    assert extracted.price_cents == 62999
    assert extracted.currency == "CAD"
    assert extracted.is_in_stock is True
    assert extracted.brand == "Nintendo"
    assert extracted.raw_snapshot["sku"] == "19296507"


def test_extract_bestbuy_api_json_sold_out():
    payload = dict(_SWITCH_2_PAYLOAD)
    payload["availability"] = {"onlineAvailability": "SoldOut", "isAvailableOnline": False}
    extracted = extract_bestbuy_api_json(payload)
    assert extracted.is_in_stock is False


def test_json_api_to_fixture_html_round_trips_through_html_extractor():
    html = json_api_to_fixture_html(_SWITCH_2_PAYLOAD)
    extracted = extract_bestbuy_html(
        html,
        url="https://www.bestbuy.ca/en-ca/product/nintendo-switch-2-console/19296507",
    )
    assert extracted.title == "Nintendo Switch 2 Console"
    assert extracted.price_cents == 62999
    assert extracted.currency == "CAD"
    assert extracted.brand == "Nintendo"


def test_json_api_to_fixture_html_requires_title_and_price():
    with pytest.raises(ValueError):
        json_api_to_fixture_html({"name": "No price product"})


def test_switch_2_fixture_json_matches_recorded_api_snapshot():
    payload = FixtureLoader().load_json("bestbuy_ca", "switch_2_in_stock")
    extracted = extract_bestbuy_api_json(payload)
    assert extracted.title == "Nintendo Switch 2 Console"
    assert extracted.price_cents == 62999
    assert extracted.currency == "CAD"
    assert extracted.brand == "Nintendo"
