"""Unit tests for the LLM clean-title policy in product_service.

Locks `_pick_display_title` independently of the router/scraper plumbing so a
future refactor of the policy stays anchored to the rule:

  Adopt the cleaned title only when it is non-empty, **strictly shorter** than
  the scraped title, and not equal to it (case-insensitive).
"""

from __future__ import annotations

import pytest

from services.product_service import _pick_display_title

_SCRAPED = "Apple AirPods Pro 3 Noise Cancelling True Wireless Earbuds"


@pytest.mark.parametrize(
    "cleaned",
    [
        None,
        "",
        "   ",
        _SCRAPED,  # equal
        _SCRAPED.lower(),  # equal, case-insensitive
        f"  {_SCRAPED}  ",  # whitespace-only diff after strip
        _SCRAPED + " with MagSafe Charging Case",  # longer
        _SCRAPED[: -len(" Earbuds")] + " Earbuds",  # exact same length
    ],
)
def test_returns_none_when_not_a_strict_improvement(cleaned: str | None):
    assert _pick_display_title(scraped=_SCRAPED, cleaned=cleaned) is None


def test_returns_cleaned_when_strictly_shorter():
    assert (
        _pick_display_title(scraped=_SCRAPED, cleaned="Apple AirPods Pro 3")
        == "Apple AirPods Pro 3"
    )
