"""Foreign exchange service interface (PRD §10.5, §7.7)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Protocol

from pydantic import BaseModel, field_validator

CANONICAL_CURRENCY = "CAD"
SUPPORTED_DISPLAY_CURRENCIES: tuple[str, ...] = ("CAD", "USD", "EUR", "GBP")


class FxServiceError(Exception):
    """Base error for FX service failures."""


class FxRateUnavailableError(FxServiceError):
    """Requested exchange rate is not available."""


class FxRate(BaseModel):
    base: str
    quote: str
    rate: Decimal
    fetched_at: datetime

    @field_validator("base", "quote")
    @classmethod
    def validate_currency_code(cls, value: str) -> str:
        if len(value) != 3 or not value.isascii() or not value.isupper():
            raise ValueError(
                "currency code must be a 3-character upper-case ISO 4217 code"
            )
        return value

    @field_validator("rate")
    @classmethod
    def validate_rate_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("rate must be > 0")
        return value

    @field_validator("fetched_at")
    @classmethod
    def validate_fetched_at_tz_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("fetched_at must be timezone-aware")
        return value


class FxRates(BaseModel):
    base: str
    rates: dict[str, FxRate]
    fetched_at: datetime

    @field_validator("fetched_at")
    @classmethod
    def validate_fetched_at_tz_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("fetched_at must be timezone-aware")
        return value


class FxService(Protocol):
    def get_rate(self, *, base: str, quote: str) -> FxRate:
        ...

    def get_rates(self, *, base: str = CANONICAL_CURRENCY) -> FxRates:
        ...

    def convert_cad_cents(self, amount_cents: int, *, quote: str) -> Decimal:
        ...


class StaticFxService:
    """In-memory FX service with fixed rates; doubles as test fake and fallback base."""

    def __init__(
        self,
        rates: Mapping[str, Decimal],
        *,
        fetched_at: datetime | None = None,
    ) -> None:
        self._rates = dict(rates)
        self._fetched_at = fetched_at or datetime.now(timezone.utc)

    def get_rate(self, *, base: str, quote: str) -> FxRate:
        if base == quote:
            return FxRate(
                base=base,
                quote=quote,
                rate=Decimal("1"),
                fetched_at=self._fetched_at,
            )
        if base != CANONICAL_CURRENCY:
            raise FxRateUnavailableError(
                f"StaticFxService only supports base={CANONICAL_CURRENCY}"
            )
        rate = self._rates.get(quote)
        if rate is None:
            raise FxRateUnavailableError(
                f"No rate configured for {base} -> {quote}"
            )
        return FxRate(
            base=base,
            quote=quote,
            rate=rate,
            fetched_at=self._fetched_at,
        )

    def get_rates(self, *, base: str = CANONICAL_CURRENCY) -> FxRates:
        if base != CANONICAL_CURRENCY:
            raise FxRateUnavailableError(
                f"StaticFxService only supports base={CANONICAL_CURRENCY}"
            )
        rates = {
            quote: FxRate(
                base=base,
                quote=quote,
                rate=rate,
                fetched_at=self._fetched_at,
            )
            for quote, rate in self._rates.items()
        }
        return FxRates(base=base, rates=rates, fetched_at=self._fetched_at)

    def convert_cad_cents(self, amount_cents: int, *, quote: str) -> Decimal:
        rate = self.get_rate(base=CANONICAL_CURRENCY, quote=quote).rate
        major_units = Decimal(amount_cents) / Decimal(100)
        return (major_units * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
