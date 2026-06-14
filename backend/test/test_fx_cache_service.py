"""CachedFxService unit tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from core.settings import Settings
from services.fx import FxServiceError
from services.fx_providers import FxProviderError
from test.fake_supabase import FakeSupabaseClient


def _settings(**overrides) -> Settings:
    return Settings(
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-key",
        **overrides,
    )


def _seed_fx_cache(
    fake: FakeSupabaseClient,
    *,
    fetched_at: datetime,
    usd: str = "0.715",
    eur: str = "0.618",
    gbp: str = "0.533",
) -> None:
    iso = fetched_at.isoformat()
    fake.fx_rates_cache["CAD_USD"] = {"pair": "CAD_USD", "rate": usd, "fetched_at": iso}
    fake.fx_rates_cache["CAD_EUR"] = {"pair": "CAD_EUR", "rate": eur, "fetched_at": iso}
    fake.fx_rates_cache["CAD_GBP"] = {"pair": "CAD_GBP", "rate": gbp, "fetched_at": iso}


def _service(fake: FakeSupabaseClient, **settings_overrides):
    from services.fx_cache_service import CachedFxService

    return CachedFxService(fake, settings=_settings(**settings_overrides))


def test_cache_hit_returns_fresh_rates_without_provider_calls():
    fake = FakeSupabaseClient()
    fetched_at = datetime.now(UTC) - timedelta(hours=1)
    _seed_fx_cache(fake, fetched_at=fetched_at)
    service = _service(fake)

    with patch("services.fx_cache_service.fetch_frankfurter_rates") as frankfurter:
        result = service.fetch_rates()

    frankfurter.assert_not_called()
    assert result.stale is False
    assert result.rates.rates["USD"].rate == Decimal("0.715")


def test_cache_miss_fetches_frankfurter_and_upserts_rows():
    fake = FakeSupabaseClient()
    service = _service(fake)
    live_rates = {
        "USD": Decimal("0.71521"),
        "EUR": Decimal("0.61834"),
        "GBP": Decimal("0.53371"),
    }

    with patch(
        "services.fx_cache_service.fetch_frankfurter_rates",
        return_value=live_rates,
    ) as frankfurter:
        result = service.fetch_rates()

    frankfurter.assert_called_once()
    assert result.stale is False
    assert set(fake.fx_rates_cache) == {"CAD_USD", "CAD_EUR", "CAD_GBP"}
    assert result.rates.rates["USD"].rate == Decimal("0.71521")


def test_frankfurter_failure_uses_exchangerate_api_fallback():
    fake = FakeSupabaseClient()
    service = _service(fake)
    live_rates = {
        "USD": Decimal("0.715"),
        "EUR": Decimal("0.618"),
        "GBP": Decimal("0.534"),
    }

    with (
        patch(
            "services.fx_cache_service.fetch_frankfurter_rates",
            side_effect=FxProviderError("down"),
        ),
        patch(
            "services.fx_cache_service.fetch_exchangerate_api_rates",
            return_value=live_rates,
        ) as fallback,
    ):
        result = service.fetch_rates()

    fallback.assert_called_once()
    assert result.stale is False
    assert result.rates.rates["GBP"].rate == Decimal("0.534")


def test_both_providers_fail_serves_stale_cache():
    fake = FakeSupabaseClient()
    stale_at = datetime.now(UTC) - timedelta(hours=48)
    _seed_fx_cache(fake, fetched_at=stale_at, usd="0.70")
    service = _service(fake)

    with (
        patch(
            "services.fx_cache_service.fetch_frankfurter_rates",
            side_effect=FxProviderError("down"),
        ),
        patch(
            "services.fx_cache_service.fetch_exchangerate_api_rates",
            side_effect=FxProviderError("down"),
        ),
    ):
        result = service.fetch_rates()

    assert result.stale is True
    assert result.rates.rates["USD"].rate == Decimal("0.70")


def test_both_providers_fail_without_cache_raises():
    fake = FakeSupabaseClient()
    service = _service(fake)

    with (
        patch(
            "services.fx_cache_service.fetch_frankfurter_rates",
            side_effect=FxProviderError("down"),
        ),
        patch(
            "services.fx_cache_service.fetch_exchangerate_api_rates",
            side_effect=FxProviderError("down"),
        ),
    ):
        with pytest.raises(FxServiceError):
            service.fetch_rates()


def test_both_providers_fail_with_partial_cache_raises():
    fake = FakeSupabaseClient()
    stale_at = datetime.now(UTC) - timedelta(hours=48)
    fake.fx_rates_cache["CAD_USD"] = {
        "pair": "CAD_USD",
        "rate": "0.70",
        "fetched_at": stale_at.isoformat(),
    }
    service = _service(fake)

    with (
        patch(
            "services.fx_cache_service.fetch_frankfurter_rates",
            side_effect=FxProviderError("down"),
        ),
        patch(
            "services.fx_cache_service.fetch_exchangerate_api_rates",
            side_effect=FxProviderError("down"),
        ),
    ):
        with pytest.raises(FxServiceError):
            service.fetch_rates()


def test_convert_cad_cents_delegates_to_cached_rate():
    fake = FakeSupabaseClient()
    _seed_fx_cache(fake, fetched_at=datetime.now(UTC))
    service = _service(fake)

    assert service.convert_cad_cents(12999, quote="USD") == Decimal("92.94")
