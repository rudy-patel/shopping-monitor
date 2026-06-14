"""FxService interface tests."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from services.fx import (
    CANONICAL_CURRENCY,
    SUPPORTED_DISPLAY_CURRENCIES,
    FxRate,
    FxRateUnavailableError,
    StaticFxService,
)


def test_static_fx_identity_rate():
    fx = StaticFxService(rates={"USD": Decimal("0.74")})
    rate = fx.get_rate(base="CAD", quote="CAD")
    assert rate.rate == Decimal("1")
    assert rate.base == "CAD"
    assert rate.quote == "CAD"


def test_static_fx_configured_rate():
    fx = StaticFxService(rates={"USD": Decimal("0.74")})
    rate = fx.get_rate(base="CAD", quote="USD")
    assert rate.rate == Decimal("0.74")


def test_static_fx_unknown_quote_raises():
    fx = StaticFxService(rates={"USD": Decimal("0.74")})
    with pytest.raises(FxRateUnavailableError):
        fx.get_rate(base="CAD", quote="JPY")


def test_convert_cad_cents_same_currency():
    fx = StaticFxService(rates={"USD": Decimal("0.74")})
    assert fx.convert_cad_cents(12345, quote="CAD") == Decimal("123.45")


def test_convert_cad_cents_with_rate_quantized_half_even():
    fx = StaticFxService(rates={"USD": Decimal("0.74")})
    assert fx.convert_cad_cents(12345, quote="USD") == Decimal("91.35")


def test_fx_rate_rejects_lowercase_currency():
    ts = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError, match="currency"):
        FxRate(base="cad", quote="USD", rate=Decimal("1"), fetched_at=ts)


def test_fx_rate_rejects_non_three_letter_currency():
    ts = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError, match="currency"):
        FxRate(base="CADD", quote="USD", rate=Decimal("1"), fetched_at=ts)


def test_fx_rate_rejects_non_positive_rate():
    ts = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError, match="rate"):
        FxRate(base="CAD", quote="USD", rate=Decimal("0"), fetched_at=ts)


def test_fx_rate_rejects_naive_fetched_at():
    with pytest.raises(ValidationError, match="fetched_at"):
        FxRate(
            base="CAD",
            quote="USD",
            rate=Decimal("1"),
            fetched_at=datetime(2026, 6, 14, 12, 0, 0),
        )


def test_currency_constants():
    assert CANONICAL_CURRENCY == "CAD"
    assert SUPPORTED_DISPLAY_CURRENCIES == ("CAD", "USD", "EUR", "GBP")
