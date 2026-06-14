"""Account delete integration test against live Supabase (disposable users only)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import scrapers.bootstrap  # noqa: F401
from core.settings import clear_settings_cache
from main import app
from test.disposable_users import (
    DISPOSABLE_EMAIL_DOMAIN,
    DISPOSABLE_EMAIL_PREFIX,
    assert_safe_to_delete,
    disposable_email,
)
from test.integration_env import require_supabase_env

pytestmark = pytest.mark.integration

TEST_PASSWORD = "delete-account-test-password-32chars!"


def _require_supabase_env() -> tuple[str, str, str]:
    return require_supabase_env()


def _service_client(url: str, service_key: str):
    from supabase import create_client

    return create_client(url, service_key)


def _anon_client(url: str, anon_key: str):
    from supabase import create_client

    return create_client(url, anon_key)


def _cleanup_disposable_users(admin) -> None:
    prefix = f"{DISPOSABLE_EMAIL_PREFIX}"
    domain = f"@{DISPOSABLE_EMAIL_DOMAIN}"
    try:
        for user in admin.auth.admin.list_users(per_page=200):
            email = getattr(user, "email", None)
            user_id = getattr(user, "id", None)
            if not email or not user_id:
                continue
            if email.startswith(prefix) and email.endswith(domain):
                assert_safe_to_delete(user_id=user_id, email=email)
                admin.auth.admin.delete_user(user_id)
    except Exception:
        pass


def _safe_delete_user(admin, user_id: str, email: str | None) -> None:
    assert_safe_to_delete(user_id=user_id, email=email)
    try:
        admin.auth.admin.delete_user(user_id)
    except Exception:
        pass


@pytest.fixture
def supabase_env():
    return _require_supabase_env()


def test_delete_account_removes_auth_user_and_profile(supabase_env, monkeypatch):
    url, anon_key, service_key = supabase_env
    admin = _service_client(url, service_key)
    anon = _anon_client(url, anon_key)

    email = disposable_email()
    user_id: str | None = None

    _cleanup_disposable_users(admin)

    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "false")
    monkeypatch.setenv("SCRAPER_MODE", "fixtures")
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    clear_settings_cache()

    try:
        created = admin.auth.admin.create_user(
            {"email": email, "password": TEST_PASSWORD, "email_confirm": True}
        )
        user_id = created.user.id
        assert_safe_to_delete(user_id=user_id, email=email)

        admin.table("profiles").insert({"user_id": user_id}).execute()

        session = anon.auth.sign_in_with_password({"email": email, "password": TEST_PASSWORD})
        token = session.session.access_token

        with TestClient(app) as client:
            response = client.delete(
                "/api/account",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 204

        with pytest.raises(Exception):
            admin.auth.admin.get_user_by_id(user_id)

        profile_rows = admin.table("profiles").select("*").eq("user_id", user_id).execute()
        assert not profile_rows.data

        product_rows = admin.table("products").select("id").eq("user_id", user_id).execute()
        assert not product_rows.data

        notification_rows = (
            admin.table("notifications").select("id").eq("user_id", user_id).execute()
        )
        assert not notification_rows.data

        user_id = None
    finally:
        if user_id is not None:
            _safe_delete_user(admin, user_id, email)
