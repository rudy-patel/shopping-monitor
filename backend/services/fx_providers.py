"""Live FX rate providers for T4.1 (Frankfurter primary, ExchangeRate-API fallback)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import httpx

from services.fx import SUPPORTED_DISPLAY_CURRENCIES

FX_QUOTES = tuple(code for code in SUPPORTED_DISPLAY_CURRENCIES if code != "CAD")
PROVIDER_TIMEOUT_S = 5.0


class FxProviderError(Exception):
    """Raised when a live FX provider request fails or returns invalid data."""


def _parse_positive_rates(raw: object, *, quotes: tuple[str, ...] = FX_QUOTES) -> dict[str, Decimal]:
    if not isinstance(raw, dict):
        raise FxProviderError("provider response rates must be an object")
    parsed: dict[str, Decimal] = {}
    for quote in quotes:
        value = raw.get(quote)
        if value is None:
            raise FxProviderError(f"missing quote: {quote}")
        try:
            rate = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise FxProviderError(f"invalid rate for {quote}") from exc
        if rate <= 0:
            raise FxProviderError(f"non-positive rate for {quote}")
        parsed[quote] = rate
    return parsed


def fetch_frankfurter_rates(
    *,
    base_url: str,
    base: str = "CAD",
    timeout_s: float = PROVIDER_TIMEOUT_S,
) -> dict[str, Decimal]:
    url = f"{base_url.rstrip('/')}/v1/latest"
    params = {"base": base, "symbols": ",".join(FX_QUOTES)}
    try:
        with httpx.Client(timeout=timeout_s) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise FxProviderError("Frankfurter request failed") from exc

    rates = payload.get("rates")
    if not isinstance(rates, dict):
        raise FxProviderError("Frankfurter response missing rates")
    return _parse_positive_rates(rates)


def fetch_exchangerate_api_rates(
    *,
    base_url: str,
    base: str = "CAD",
    timeout_s: float = PROVIDER_TIMEOUT_S,
) -> dict[str, Decimal]:
    url = f"{base_url.rstrip('/')}/{base}"
    try:
        with httpx.Client(timeout=timeout_s) as client:
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise FxProviderError("ExchangeRate-API request failed") from exc

    if payload.get("result") != "success":
        raise FxProviderError("ExchangeRate-API result was not success")

    rates = payload.get("rates")
    if not isinstance(rates, dict):
        raise FxProviderError("ExchangeRate-API response missing rates")
    return _parse_positive_rates(rates)
