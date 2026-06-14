"""Account router unit tests."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.settings import clear_settings_cache
from routers.account import router as account_router
from services.profile_service import PROFILE_DEFAULTS
from test.fake_supabase import FakeSupabaseClient

DEV_USER_ID = "00000000-0000-0000-0000-000000000001"
DISPOSABLE_USER_ID = "22222222-2222-2222-2222-222222222222"
DISPOSABLE_EMAIL = "delete-test@shopping-monitor-test.invalid"


def make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(account_router)
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
    monkeypatch.setattr("services.account_service.get_service_role_client", lambda: client)
    return client


def _seed_disposable_user(fake: FakeSupabaseClient) -> None:
    now = datetime.now(UTC).isoformat()
    fake.auth_users[DISPOSABLE_USER_ID] = {"email": DISPOSABLE_EMAIL}
    fake.profiles[DISPOSABLE_USER_ID] = {
        **PROFILE_DEFAULTS,
        "user_id": DISPOSABLE_USER_ID,
        "created_at": now,
        "updated_at": now,
    }


def _mock_jwt_for_disposable(monkeypatch) -> None:
    def return_claims(_token, _settings):
        return {
            "sub": DISPOSABLE_USER_ID,
            "email": DISPOSABLE_EMAIL,
            "role": "authenticated",
            "aud": "authenticated",
        }

    monkeypatch.setattr("core.auth._decode_jwt", return_claims)


@pytest.fixture
def account_client(auth_env, fake_client, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "false")
    clear_settings_cache()
    _mock_jwt_for_disposable(monkeypatch)
    return TestClient(make_app()), fake_client


def test_delete_account_success(account_client):
    client, fake = account_client
    _seed_disposable_user(fake)

    response = client.delete("/api/account", headers={"Authorization": "Bearer fake"})

    assert response.status_code == 204
    assert response.content == b""
    assert DISPOSABLE_USER_ID not in fake.auth_users
    assert DISPOSABLE_USER_ID not in fake.profiles


def test_delete_account_auth_bypass_returns_403(auth_env, fake_client, monkeypatch):
    _fake = fake_client
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "true")
    clear_settings_cache()
    now = datetime.now(UTC).isoformat()
    _fake.auth_users[DEV_USER_ID] = {"email": "dev@local.test"}
    _fake.profiles[DEV_USER_ID] = {
        **PROFILE_DEFAULTS,
        "user_id": DEV_USER_ID,
        "created_at": now,
        "updated_at": now,
    }
    client = TestClient(make_app())

    response = client.delete("/api/account")

    assert response.status_code == 403
    assert response.json()["detail"] == "Account deletion is disabled in auth bypass mode"
    assert DEV_USER_ID in _fake.auth_users
    assert DEV_USER_ID in _fake.profiles


def test_delete_account_user_not_found(account_client):
    client, _fake = account_client

    response = client.delete("/api/account", headers={"Authorization": "Bearer fake"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Account not found"


def test_delete_account_admin_failure(account_client):
    client, fake = account_client
    _seed_disposable_user(fake)
    fake.force_delete_user_error = True

    response = client.delete("/api/account", headers={"Authorization": "Bearer fake"})

    assert response.status_code == 502
    assert response.json()["detail"] == "Could not delete account"
    assert DISPOSABLE_USER_ID in fake.auth_users


def test_delete_account_second_delete_returns_404(account_client):
    client, fake = account_client
    _seed_disposable_user(fake)

    first = client.delete("/api/account", headers={"Authorization": "Bearer fake"})
    second = client.delete("/api/account", headers={"Authorization": "Bearer fake"})

    assert first.status_code == 204
    assert second.status_code == 404


def test_delete_account_requires_auth_when_bypass_disabled(auth_env, fake_client, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "false")
    clear_settings_cache()
    client = TestClient(make_app())

    response = client.delete("/api/account")

    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


def test_delete_account_rejects_protected_user(auth_env, fake_client, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "false")
    clear_settings_cache()

    def return_claims(_token, _settings):
        return {
            "sub": DEV_USER_ID,
            "email": "dev@local.test",
            "role": "authenticated",
            "aud": "authenticated",
        }

    monkeypatch.setattr("core.auth._decode_jwt", return_claims)
    client = TestClient(make_app())

    response = client.delete("/api/account", headers={"Authorization": "Bearer fake"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Cannot delete protected account"
