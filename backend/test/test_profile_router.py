"""Profile router unit tests."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.settings import clear_settings_cache
from routers.profile import router as profile_router
from services.profile_service import PROFILE_DEFAULTS
from test.fake_supabase import FakeSupabaseClient

DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


def make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(profile_router)
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
def fake_client(monkeypatch):
    client = FakeSupabaseClient()
    monkeypatch.setattr("services.profile_service.get_client", lambda: client)
    return client


@pytest.fixture
def profile_client(auth_env, fake_client, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "true")
    clear_settings_cache()
    return TestClient(make_app()), fake_client


def _seed_profile(fake: FakeSupabaseClient, user_id: str, **overrides) -> dict:
    now = datetime.now(UTC).isoformat()
    row = {
        **PROFILE_DEFAULTS,
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
        **overrides,
    }
    fake.profiles[user_id] = row
    return row


def test_get_profile_upserts_defaults_for_new_user(profile_client):
    client, fake = profile_client

    response = client.get("/api/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == DEV_USER_ID
    assert body["display_currency"] == "CAD"
    assert body["default_threshold_pct"] == 20
    assert body["theme"] == "light"
    assert len(fake.profiles) == 1


def test_get_profile_is_idempotent(profile_client):
    client, fake = profile_client

    first = client.get("/api/profile")
    second = client.get("/api/profile")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(fake.profiles) == 1


def test_get_profile_returns_existing_row_when_present(profile_client):
    client, fake = profile_client
    _seed_profile(fake, DEV_USER_ID, display_currency="USD", default_threshold_pct=15)

    response = client.get("/api/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["display_currency"] == "USD"
    assert body["default_threshold_pct"] == 15
    assert len(fake.profiles) == 1


def test_get_profile_concurrent_insert_recovers(profile_client):
    client, fake = profile_client
    _seed_profile(fake, DEV_USER_ID, display_currency="EUR")
    fake.force_duplicate_on_insert = True

    response = client.get("/api/profile")

    assert response.status_code == 200
    assert response.json()["display_currency"] == "EUR"
    assert len(fake.profiles) == 1


def test_patch_profile_updates_supplied_fields_only(profile_client):
    client, _fake = profile_client
    client.get("/api/profile")

    response = client.patch("/api/profile", json={"display_currency": "USD"})

    assert response.status_code == 200
    body = response.json()
    assert body["display_currency"] == "USD"
    assert body["default_threshold_pct"] == 20


def test_patch_profile_creates_then_updates(profile_client):
    client, fake = profile_client

    response = client.patch("/api/profile", json={"display_currency": "GBP"})

    assert response.status_code == 200
    assert response.json()["display_currency"] == "GBP"
    assert DEV_USER_ID in fake.profiles


def test_patch_profile_empty_body_returns_400(profile_client):
    client, _fake = profile_client
    client.get("/api/profile")

    response = client.patch("/api/profile", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "No fields to update"


@pytest.mark.parametrize(
    ("payload", "loc"),
    [
        ({"display_currency": "XYZ"}, "display_currency"),
        ({"default_threshold_pct": 0}, "default_threshold_pct"),
        ({"default_threshold_pct": 96}, "default_threshold_pct"),
        ({"theme": "rainbow"}, "theme"),
        ({"revisit_stale_days": 6}, "revisit_stale_days"),
        ({"revisit_stale_days": 366}, "revisit_stale_days"),
        ({"foo": 1}, "foo"),
    ],
)
def test_patch_profile_validation_errors(profile_client, payload, loc):
    client, _fake = profile_client
    client.get("/api/profile")

    response = client.patch("/api/profile", json=payload)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(err["loc"][-1] == loc for err in errors)


def test_requires_auth_when_bypass_disabled(auth_env, fake_client, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "false")
    clear_settings_cache()
    client = TestClient(make_app())

    response = client.get("/api/profile")

    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"
