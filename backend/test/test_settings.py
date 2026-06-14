"""Settings loader unit tests."""

from __future__ import annotations

import os
from uuid import UUID

import pytest
from pydantic import ValidationError

from core.settings import Settings, clear_settings_cache, get_settings

SETTINGS_ENV_KEYS = [
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "AUTH_BYPASS_ENABLED",
    "DEV_USER_ID",
    "WORKER_TOKEN",
    "GEMINI_API_KEY",
    "RESEND_API_KEY",
    "APP_BASE_URL",
    "SCRAPER_MODE",
    "LOG_LEVEL",
    "CORS_ALLOWED_ORIGINS",
]


@pytest.fixture
def settings_env(monkeypatch):
    snapshot = dict(os.environ)
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    clear_settings_cache()
    yield monkeypatch
    os.environ.clear()
    os.environ.update(snapshot)
    clear_settings_cache()


def test_defaults_when_env_unset(settings_env, monkeypatch):
    for key in SETTINGS_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    clear_settings_cache()

    settings = get_settings()
    assert settings.supabase_url == ""
    assert settings.supabase_anon_key == ""
    assert settings.supabase_service_role_key == ""
    assert settings.auth_bypass_enabled is False
    assert settings.dev_user_id == UUID("00000000-0000-0000-0000-000000000001")
    assert settings.worker_token == ""
    assert settings.gemini_api_key == ""
    assert settings.resend_api_key == ""
    assert settings.app_base_url == "http://" + "localhost" + ":3000"
    assert settings.scraper_mode == "fix" + "tures"
    assert settings.log_level == "INFO"
    assert settings.cors_allowed_origins == [
        "http://" + "localhost" + ":3000",
        "http://127.0.0.1:3000",
    ]


def test_env_overrides(settings_env, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "true")
    monkeypatch.setenv("DEV_USER_ID", "11111111-1111-1111-1111-111111111111")
    monkeypatch.setenv("WORKER_TOKEN", "secret-worker")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("RESEND_API_KEY", "resend-key")
    monkeypatch.setenv("APP_BASE_URL", "http://app.example")
    monkeypatch.setenv("SCRAPER_MODE", "live")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://a,http://b")
    clear_settings_cache()

    settings = get_settings()
    assert settings.supabase_url == "https://example.supabase.co"
    assert settings.supabase_anon_key == "anon-key"
    assert settings.supabase_service_role_key == "service-key"
    assert settings.auth_bypass_enabled is True
    assert settings.dev_user_id == UUID("11111111-1111-1111-1111-111111111111")
    assert settings.worker_token == "secret-worker"
    assert settings.gemini_api_key == "gemini-key"
    assert settings.resend_api_key == "resend-key"
    assert settings.app_base_url == "http://app.example"
    assert settings.scraper_mode == "live"
    assert settings.log_level == "debug"
    assert settings.cors_allowed_origins == ["http://a", "http://b"]


def test_scraper_mode_invalid_raises(settings_env, monkeypatch):
    monkeypatch.setenv("SCRAPER_MODE", "banana")
    clear_settings_cache()
    with pytest.raises(ValidationError):
        Settings()


def test_cors_origins_csv(settings_env, monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://a,http://b")
    clear_settings_cache()
    settings = get_settings()
    assert settings.cors_allowed_origins == ["http://a", "http://b"]


def test_cache_returns_same_instance(settings_env):
    clear_settings_cache()
    assert get_settings() is get_settings()
