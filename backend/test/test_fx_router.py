"""FX router unit tests."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.settings import clear_settings_cache
from routers.fx import router as fx_router
from services.fx_providers import FxProviderError
from test.fake_supabase import FakeSupabaseClient
from test.test_fx_cache_service import _seed_fx_cache, _service


def make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(fx_router)
    return app


@pytest.fixture
def auth_env(monkeypatch):
    snapshot = dict(os.environ)
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    clear_settings_cache()
    yield monkeypatch
    os.environ.clear()
    os.environ.update(snapshot)
    clear_settings_cache()


@pytest.fixture
def fx_client(auth_env, monkeypatch):
    auth_env.setenv("AUTH_BYPASS_ENABLED", "true")
    clear_settings_cache()
    fake = FakeSupabaseClient()
    monkeypatch.setattr("services.factory.get_service_role_client", lambda: fake)
    monkeypatch.setattr("routers.fx.get_fx_service", lambda: _service(fake))
    return TestClient(make_app()), fake


def test_get_fx_rates_requires_auth(auth_env):
    auth_env.delenv("AUTH_BYPASS_ENABLED", raising=False)
    clear_settings_cache()
    client = TestClient(make_app())

    response = client.get("/api/fx/rates")

    assert response.status_code == 401


def test_get_fx_rates_returns_decimal_strings(fx_client):
    client, fake = fx_client
    _seed_fx_cache(fake, fetched_at=datetime.now(UTC))

    response = client.get("/api/fx/rates")

    assert response.status_code == 200
    body = response.json()
    assert body["base"] == "CAD"
    assert body["stale"] is False
    assert body["rates"]["CAD"] == "1"
    assert body["rates"]["USD"] == "0.715"


def test_get_fx_rates_returns_stale_flag(fx_client):
    client, fake = fx_client
    _seed_fx_cache(fake, fetched_at=datetime.now(UTC) - timedelta(hours=48))

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
        response = client.get("/api/fx/rates")

    assert response.status_code == 200
    assert response.json()["stale"] is True


def test_get_fx_rates_returns_503_when_unavailable(fx_client):
    client, _fake = fx_client

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
        response = client.get("/api/fx/rates")

    assert response.status_code == 503
