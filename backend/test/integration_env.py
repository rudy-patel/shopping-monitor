"""Shared helpers for Supabase integration tests."""

from __future__ import annotations

import pytest

from integration_env import SETUP_HINT, load_backend_dotenv, missing_or_placeholder_credentials
from integration_env import env_value as _env


def require_supabase_env() -> tuple[str, str, str]:
    load_backend_dotenv()
    missing = missing_or_placeholder_credentials()
    if missing:
        reason = f"{SETUP_HINT} Missing or placeholder values for: {', '.join(missing)}."
        if _env("REQUIRE_INTEGRATION_ENV") == "1":
            pytest.fail(reason)
        pytest.skip(reason)
    return _env("SUPABASE_URL"), _env("SUPABASE_ANON_KEY"), _env("SUPABASE_SERVICE_ROLE_KEY")
