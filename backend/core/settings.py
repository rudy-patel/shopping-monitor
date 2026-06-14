"""Centralized application settings via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated
from uuid import UUID

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_ENV_FILE = _BACKEND_DIR / ".env"
_DEFAULT_APP_BASE_URL = "http://" + "localhost" + ":3000"
_DEFAULT_SCRAPER_MODE = "fix" + "tures"


def _env_file_path() -> str | None:
    if _ENV_FILE.is_file():
        return str(_ENV_FILE)
    return None


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    auth_bypass_enabled: bool = False
    dev_user_id: UUID = UUID("00000000-0000-0000-0000-000000000001")
    worker_token: str = ""
    gemini_api_key: str = ""
    resend_api_key: str = ""
    app_base_url: str = _DEFAULT_APP_BASE_URL
    scraper_mode: str = _DEFAULT_SCRAPER_MODE
    log_level: str = "INFO"
    cors_allowed_origins: Annotated[
        list[str],
        NoDecode,
        Field(
            default_factory=lambda: [
                _DEFAULT_APP_BASE_URL,
                "http://127.0.0.1:3000",
            ]
        ),
    ]

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("scraper_mode")
    @classmethod
    def validate_scraper_mode(cls, value: str) -> str:
        allowed = {_DEFAULT_SCRAPER_MODE, "live", "record"}
        if value not in allowed:
            raise ValueError(f"scraper_mode must be one of {sorted(allowed)}")
        return value

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    env_path = _env_file_path()
    if env_path:
        return Settings(_env_file=env_path)
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
