"""Tests for Nike.ca extraction."""

from __future__ import annotations

from scrapers.extraction.nike import extract_nike_html


def test_extract_from_recorded_in_stock_fixture():
    from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret

    html = FixtureLoader().load_text("nike_ca", "in_stock")
    extracted = extract_nike_html(
        html,
        "https://www.nike.com/ca/t/air-force-1-07-mens-shoes-nM2To5/CW2288-111",
    )
    assert extracted.title == "Nike Air Force 1 '07 Men's Shoes"
    assert extracted.price_cents == 15000
    assert extracted.is_in_stock is True
    assert len(extracted.available_variants) >= 2


def test_extract_out_of_stock_fixture():
    from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret

    html = FixtureLoader().load_text("nike_ca", "out_of_stock")
    extracted = extract_nike_html(
        html,
        "https://www.nike.com/ca/t/air-force-1-07-mens-shoes-nM2To5/CW2288-111",
    )
    assert extracted.is_in_stock is False
    assert extracted.price_cents == 15000
