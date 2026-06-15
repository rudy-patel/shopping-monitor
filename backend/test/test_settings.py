"""Settings loader unit tests."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from core.settings import (
    DEFAULT_APP_BASE_URL,
    DEFAULT_CORS_ORIGINS,
    DEFAULT_GEMINI_CATEGORIZE_TIMEOUT_S,
    DEFAULT_GEMINI_DISCOVER_TIMEOUT_S,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GEMINI_SEARCH_MODEL,
    DEFAULT_GEMINI_SEARCH_TIMEOUT_S,
    DEFAULT_SCRAPER_MODE,
    DEFAULT_SEARCH_CACHE_TTL_HOURS,
    PRODUCTION_APP_BASE_URL,
    Settings,
    clear_settings_cache,
    effective_app_base_url,
    get_settings,
)

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_ENV_EXAMPLE_PATH = _BACKEND_DIR / ".env.example"

SETTINGS_ENV_KEYS = [
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "AUTH_BYPASS_ENABLED",
    "DEV_USER_ID",
    "WORKER_TOKEN",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GEMINI_SEARCH_MODEL",
    "GEMINI_CATEGORIZE_TIMEOUT_S",
    "GEMINI_DISCOVER_TIMEOUT_S",
    "GEMINI_SEARCH_TIMEOUT_S",
    "SEARCH_CACHE_TTL_HOURS",
    "RESEND_API_KEY",
    "RESEND_FROM_EMAIL",
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
    assert settings.gemini_model == DEFAULT_GEMINI_MODEL
    assert settings.gemini_search_model == DEFAULT_GEMINI_SEARCH_MODEL
    assert settings.gemini_categorize_timeout_s == DEFAULT_GEMINI_CATEGORIZE_TIMEOUT_S
    assert settings.gemini_discover_timeout_s == DEFAULT_GEMINI_DISCOVER_TIMEOUT_S
    assert settings.gemini_search_timeout_s == DEFAULT_GEMINI_SEARCH_TIMEOUT_S
    assert settings.search_cache_ttl_hours == DEFAULT_SEARCH_CACHE_TTL_HOURS
    assert settings.resend_api_key == ""
    assert settings.app_base_url == DEFAULT_APP_BASE_URL
    assert settings.scraper_mode == DEFAULT_SCRAPER_MODE
    assert settings.log_level == "INFO"
    assert settings.cors_allowed_origins == DEFAULT_CORS_ORIGINS


def test_env_overrides(settings_env, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "true")
    monkeypatch.setenv("DEV_USER_ID", "11111111-1111-1111-1111-111111111111")
    monkeypatch.setenv("WORKER_TOKEN", "secret-worker")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")
    monkeypatch.setenv("GEMINI_SEARCH_MODEL", "gemini-test-search-model")
    monkeypatch.setenv("GEMINI_CATEGORIZE_TIMEOUT_S", "2.5")
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
    assert settings.gemini_model == "gemini-test-model"
    assert settings.gemini_search_model == "gemini-test-search-model"
    assert settings.gemini_categorize_timeout_s == 2.5
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


def test_env_example_documents_settings_keys():
    """backend/.env.example should list env vars that Settings reads for local setup."""
    contents = _ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    documented = {
        line.split("=", 1)[0]
        for line in contents.splitlines()
        if line and not line.startswith("#") and "=" in line
    }
    expected = {key for key in SETTINGS_ENV_KEYS if key != "DEV_USER_ID"}
    missing = expected - documented
    assert not missing, f"backend/.env.example missing keys: {sorted(missing)}"


def test_effective_app_base_url_local_dev():
    settings = Settings(auth_bypass_enabled=True, app_base_url=DEFAULT_APP_BASE_URL)
    assert effective_app_base_url(settings) == DEFAULT_APP_BASE_URL.rstrip("/")


def test_effective_app_base_url_production_fallback():
    settings = Settings(auth_bypass_enabled=False, app_base_url=DEFAULT_APP_BASE_URL)
    assert effective_app_base_url(settings) == PRODUCTION_APP_BASE_URL


def test_effective_app_base_url_explicit_production_override():
    settings = Settings(
        auth_bypass_enabled=False,
        app_base_url="https://custom.example",
    )
    assert effective_app_base_url(settings) == "https://custom.example"
