"""Unit tests for integration credential validation."""

from __future__ import annotations

from integration_env import (
    is_placeholder_value,
    missing_or_placeholder_credentials,
)


def test_placeholder_url_is_rejected():
    assert is_placeholder_value("SUPABASE_URL", "https://your-project-id.supabase.co")
    assert not is_placeholder_value("SUPABASE_URL", "https://abc123.supabase.co")


def test_placeholder_keys_are_rejected():
    assert is_placeholder_value("SUPABASE_ANON_KEY", "your-anon-or-publishable-key")
    assert not is_placeholder_value(
        "SUPABASE_ANON_KEY",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example",
    )


def test_missing_or_placeholder_reports_all_required_keys():
    missing = missing_or_placeholder_credentials(
        {
            "SUPABASE_URL": "https://your-project-id.supabase.co",
            "SUPABASE_ANON_KEY": "your-anon-or-publishable-key",
            "SUPABASE_SERVICE_ROLE_KEY": "your-service-role-secret",
        }
    )
    assert missing == [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
    ]
