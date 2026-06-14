"""Auth dependency unit tests."""

from __future__ import annotations

import os

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from core.auth import CurrentUser, _InvalidToken, get_current_user
from core.settings import clear_settings_cache


def make_app() -> FastAPI:
    app = FastAPI()

    @app.get("/whoami")
    async def whoami(user: CurrentUser = Depends(get_current_user)):
        return {
            "user_id": str(user.user_id),
            "email": user.email,
            "role": user.role,
        }

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


def test_auth_bypass_returns_dev_user(auth_env, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "true")
    clear_settings_cache()
    client = TestClient(make_app())

    response = client.get("/whoami")
    assert response.status_code == 200
    assert response.json()["user_id"] == "00000000-0000-0000-0000-000000000001"


def test_auth_bypass_off_missing_header(auth_env, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "false")
    clear_settings_cache()
    client = TestClient(make_app())

    response = client.get("/whoami")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


def test_auth_bypass_off_malformed_header(auth_env, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "false")
    clear_settings_cache()
    client = TestClient(make_app())

    response = client.get("/whoami", headers={"Authorization": "Token xyz"})
    assert response.status_code == 401


def test_auth_bypass_off_invalid_token(auth_env, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "false")
    clear_settings_cache()

    def raise_invalid(_token, _settings):
        raise _InvalidToken

    monkeypatch.setattr("core.auth._decode_jwt", raise_invalid)
    client = TestClient(make_app())

    response = client.get("/whoami", headers={"Authorization": "Bearer fake"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_auth_bypass_off_valid_token(auth_env, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "false")
    clear_settings_cache()

    def return_claims(_token, _settings):
        return {
            "sub": "11111111-1111-1111-1111-111111111111",
            "email": "u@example.com",
            "role": "authenticated",
            "aud": "authenticated",
        }

    monkeypatch.setattr("core.auth._decode_jwt", return_claims)
    client = TestClient(make_app())

    response = client.get("/whoami", headers={"Authorization": "Bearer fake"})
    assert response.status_code == 200
    assert response.json()["user_id"] == "11111111-1111-1111-1111-111111111111"
    assert response.json()["email"] == "u@example.com"


def test_auth_token_missing_sub(auth_env, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "false")
    clear_settings_cache()

    def return_claims(_token, _settings):
        return {"email": "u@example.com", "aud": "authenticated"}

    monkeypatch.setattr("core.auth._decode_jwt", return_claims)
    client = TestClient(make_app())

    response = client.get("/whoami", headers={"Authorization": "Bearer fake"})
    assert response.status_code == 401


def test_auth_token_invalid_sub_uuid(auth_env, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "false")
    clear_settings_cache()

    def return_claims(_token, _settings):
        return {"sub": "not-a-uuid", "aud": "authenticated"}

    monkeypatch.setattr("core.auth._decode_jwt", return_claims)
    client = TestClient(make_app())

    response = client.get("/whoami", headers={"Authorization": "Bearer fake"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"
    assert response.headers.get("www-authenticate") == "Bearer"
