"""Shared Supabase integration-test credential validation."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REQUIRED_ENV = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY")

_PLACEHOLDER_URL = "https://your-project-id.supabase.co"
_PLACEHOLDER_EXACT_KEYS = frozenset(
    {
        "your-anon-or-publishable-key",
        "your-service-role-secret",
    }
)

SETUP_HINT = (
    "Integration tests need a real Supabase project (H1). "
    "Set SUPABASE_URL, SUPABASE_ANON_KEY, and SUPABASE_SERVICE_ROLE_KEY in backend/.env, "
    "or export them in your shell, or set SUPABASE_ACCESS_TOKEN + SUPABASE_PROJECT_REF "
    "and run `make setup-integration-env`."
)


def backend_dotenv_path() -> Path:
    return Path(__file__).resolve().parent / ".env"


def load_backend_dotenv(*, override: bool = False) -> None:
    path = backend_dotenv_path()
    if path.is_file():
        load_dotenv(path, override=override)


def env_value(name: str) -> str:
    return (os.getenv(name) or "").strip()


def is_placeholder_value(name: str, value: str) -> bool:
    if not value:
        return True
    if name == "SUPABASE_URL":
        return value == _PLACEHOLDER_URL or "your-project-id" in value
    if name in {"SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"}:
        lowered = value.lower()
        if lowered in _PLACEHOLDER_EXACT_KEYS:
            return True
        return lowered.startswith("your-")
    return False


def read_supabase_credentials() -> dict[str, str]:
    return {name: env_value(name) for name in REQUIRED_ENV}


def missing_or_placeholder_credentials(values: dict[str, str] | None = None) -> list[str]:
    values = values or read_supabase_credentials()
    return [
        name
        for name in REQUIRED_ENV
        if not values.get(name) or is_placeholder_value(name, values[name])
    ]
