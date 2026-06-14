"""Production FxService backed by fx_rates_cache and live providers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from typing import TYPE_CHECKING

from services.fx import (
    CANONICAL_CURRENCY,
    FxRate,
    FxRateUnavailableError,
    FxRates,
    FxServiceError,
)
from services.fx_providers import (
    FX_QUOTES,
    FxProviderError,
    fetch_exchangerate_api_rates,
    fetch_frankfurter_rates,
)

if TYPE_CHECKING:
    from supabase import Client

    from core.settings import Settings

logger = logging.getLogger(__name__)

FX_CACHE_PAIRS = tuple(f"CAD_{quote}" for quote in FX_QUOTES)


@dataclass(frozen=True)
class CachedFxRatesResult:
    rates: FxRates
    stale: bool


class CachedFxService:
    """Fetch CAD-based FX rates with 24h DB cache and provider fallback chain."""

    def __init__(self, client: Client, *, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    def fetch_rates(self, *, base: str = CANONICAL_CURRENCY) -> CachedFxRatesResult:
        if base != CANONICAL_CURRENCY:
            raise FxRateUnavailableError(
                f"CachedFxService only supports base={CANONICAL_CURRENCY}"
            )

        cached_rows = self._read_cache_rows()
        if cached_rows and self._cache_is_fresh(cached_rows):
            return CachedFxRatesResult(
                rates=self._rows_to_fx_rates(cached_rows),
                stale=False,
            )

        try:
            live_rates, fetched_at = self._fetch_live_rates()
            self._upsert_cache(live_rates, fetched_at=fetched_at)
            return CachedFxRatesResult(
                rates=self._build_fx_rates(live_rates, fetched_at=fetched_at),
                stale=False,
            )
        except FxProviderError:
            if cached_rows and self._cache_is_complete(cached_rows):
                logger.warning("FX providers failed; serving stale cached rates")
                return CachedFxRatesResult(
                    rates=self._rows_to_fx_rates(cached_rows),
                    stale=True,
                )
            raise FxServiceError("FX rates unavailable and cache is empty") from None

    def get_rates(self, *, base: str = CANONICAL_CURRENCY) -> FxRates:
        return self.fetch_rates(base=base).rates

    def get_rate(self, *, base: str, quote: str) -> FxRate:
        if base == quote:
            fetched_at = datetime.now(UTC)
            return FxRate(base=base, quote=quote, rate=Decimal("1"), fetched_at=fetched_at)
        rates = self.get_rates(base=base)
        fx_rate = rates.rates.get(quote)
        if fx_rate is None:
            raise FxRateUnavailableError(f"No rate available for {base} -> {quote}")
        return fx_rate

    def convert_cad_cents(self, amount_cents: int, *, quote: str) -> Decimal:
        rate = self.get_rate(base=CANONICAL_CURRENCY, quote=quote).rate
        major_units = Decimal(amount_cents) / Decimal(100)
        return (major_units * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

    def _read_cache_rows(self) -> list[dict]:
        response = (
            self._client.table("fx_rates_cache")
            .select("pair,rate,fetched_at")
            .in_("pair", list(FX_CACHE_PAIRS))
            .execute()
        )
        rows = response.data or []
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)]

    def _cache_is_complete(self, rows: list[dict]) -> bool:
        pairs = {row.get("pair") for row in rows}
        return set(FX_CACHE_PAIRS).issubset(pairs)

    def _cache_is_fresh(self, rows: list[dict]) -> bool:
        if not self._cache_is_complete(rows):
            return False
        ttl = timedelta(hours=self._settings.fx_cache_ttl_hours)
        now = datetime.now(UTC)
        oldest: datetime | None = None
        for row in rows:
            fetched_at = self._parse_fetched_at(row.get("fetched_at"))
            if oldest is None or fetched_at < oldest:
                oldest = fetched_at
        if oldest is None:
            return False
        return now - oldest <= ttl

    def _fetch_live_rates(self) -> tuple[dict[str, Decimal], datetime]:
        fetched_at = datetime.now(UTC)
        try:
            rates = fetch_frankfurter_rates(
                base_url=self._settings.frankfurter_base_url,
                base=CANONICAL_CURRENCY,
            )
            return rates, fetched_at
        except FxProviderError:
            rates = fetch_exchangerate_api_rates(
                base_url=self._settings.exchangerate_api_open_url,
                base=CANONICAL_CURRENCY,
            )
            return rates, fetched_at

    def _upsert_cache(self, rates: dict[str, Decimal], *, fetched_at: datetime) -> None:
        payload = [
            {
                "pair": f"CAD_{quote}",
                "rate": str(rate),
                "fetched_at": fetched_at.isoformat(),
            }
            for quote, rate in rates.items()
        ]
        self._client.table("fx_rates_cache").upsert(payload).execute()

    def _rows_to_fx_rates(self, rows: list[dict]) -> FxRates:
        by_pair = {str(row["pair"]): row for row in rows if row.get("pair")}
        fetched_at = max(self._parse_fetched_at(row["fetched_at"]) for row in by_pair.values())
        live_rates = {
            pair.split("_", 1)[1]: Decimal(str(by_pair[pair]["rate"]))
            for pair in FX_CACHE_PAIRS
            if pair in by_pair
        }
        return self._build_fx_rates(live_rates, fetched_at=fetched_at)

    def _build_fx_rates(self, rates: dict[str, Decimal], *, fetched_at: datetime) -> FxRates:
        fx_rates = {
            quote: FxRate(
                base=CANONICAL_CURRENCY,
                quote=quote,
                rate=rate,
                fetched_at=fetched_at,
            )
            for quote, rate in rates.items()
        }
        return FxRates(base=CANONICAL_CURRENCY, rates=fx_rates, fetched_at=fetched_at)

    @staticmethod
    def _parse_fetched_at(value: object) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed
        raise FxServiceError("invalid fetched_at in fx_rates_cache")
