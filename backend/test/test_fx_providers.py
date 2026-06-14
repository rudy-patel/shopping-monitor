"""FX provider parsing tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from services.fx_providers import FxProviderError, _parse_positive_rates


def test_parse_positive_rates_accepts_decimal_strings():
    parsed = _parse_positive_rates({"USD": "0.715", "EUR": "0.618", "GBP": "0.533"})
    assert parsed["USD"] == Decimal("0.715")


def test_parse_positive_rates_rejects_missing_quote():
    with pytest.raises(FxProviderError, match="missing quote"):
        _parse_positive_rates({"USD": "0.715", "EUR": "0.618"})


def test_parse_positive_rates_rejects_non_positive_rate():
    with pytest.raises(FxProviderError, match="non-positive"):
        _parse_positive_rates({"USD": "0", "EUR": "0.618", "GBP": "0.533"})
