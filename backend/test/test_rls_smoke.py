"""RLS smoke test: user A's rows are invisible to user B (requires live Supabase)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

pytestmark = pytest.mark.integration

_SKIP_REASON = "SUPABASE_URL, SUPABASE_ANON_KEY, or SUPABASE_SERVICE_ROLE_KEY not set"

USER_A_EMAIL = "a@t1-1-rls-smoke.invalid"
USER_B_EMAIL = "b@t1-1-rls-smoke.invalid"
TEST_PASSWORD = "t1-1-rls-smoke-test-password-32chars!"


def _load_env() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    load_dotenv(backend_root / ".env")


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def _require_supabase_env() -> tuple[str, str, str]:
    _load_env()
    url = _env("SUPABASE_URL")
    anon_key = _env("SUPABASE_ANON_KEY")
    service_key = _env("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not anon_key or not service_key:
        if _env("REQUIRE_INTEGRATION_ENV") == "1":
            pytest.fail(_SKIP_REASON)
        pytest.skip(_SKIP_REASON)
    return url, anon_key, service_key


def _service_client(url: str, service_key: str):
    from supabase import create_client

    return create_client(url, service_key)


def _anon_client(url: str, anon_key: str):
    from supabase import create_client

    return create_client(url, anon_key)


def _auth_client(url: str, anon_key: str, access_token: str):
    client = _anon_client(url, anon_key)
    client.postgrest.auth(access_token)
    return client


def _assert_mutation_denied(fn) -> None:
    """RLS denials may raise or return an empty data payload."""
    try:
        result = fn()
    except Exception:
        return
    assert not result.data


def _cleanup_test_users(admin) -> None:
    targets = {USER_A_EMAIL, USER_B_EMAIL}
    try:
        for user in admin.auth.admin.list_users(per_page=200):
            if user.email in targets:
                admin.auth.admin.delete_user(user.id)
    except Exception:
        pass


@pytest.fixture
def supabase_env():
    return _require_supabase_env()


def test_rls_products_isolation(supabase_env):
    url, anon_key, service_key = supabase_env
    admin = _service_client(url, service_key)
    anon = _anon_client(url, anon_key)

    user_a_id: str | None = None
    user_b_id: str | None = None
    product_id: str | None = None

    _cleanup_test_users(admin)

    try:
        user_a = admin.auth.admin.create_user(
            {"email": USER_A_EMAIL, "password": TEST_PASSWORD, "email_confirm": True}
        )
        user_b = admin.auth.admin.create_user(
            {"email": USER_B_EMAIL, "password": TEST_PASSWORD, "email_confirm": True}
        )
        user_a_id = user_a.user.id
        user_b_id = user_b.user.id

        admin.table("profiles").insert({"user_id": user_a_id}).execute()

        product_row = (
            admin.table("products")
            .insert(
                {
                    "user_id": user_a_id,
                    "title": "RLS smoke product",
                    "category": "other",
                    "category_source": "default_other",
                }
            )
            .execute()
        )
        product_id = product_row.data[0]["id"]

        session_b = anon.auth.sign_in_with_password(
            {"email": USER_B_EMAIL, "password": TEST_PASSWORD}
        )
        client_b = _auth_client(url, anon_key, session_b.session.access_token)

        rows_b = client_b.table("products").select("*").execute()
        assert len(rows_b.data) == 0

        _assert_mutation_denied(
            lambda: client_b.table("products")
            .update({"title": "hijacked"})
            .eq("id", product_id)
            .execute()
        )
        _assert_mutation_denied(
            lambda: client_b.table("products")
            .insert(
                {
                    "user_id": user_a_id,
                    "title": "forged",
                    "category": "other",
                    "category_source": "default_other",
                }
            )
            .execute()
        )

        fx_rows = client_b.table("fx_rates_cache").select("*").execute()
        assert len(fx_rows.data) == 0

        session_a = anon.auth.sign_in_with_password(
            {"email": USER_A_EMAIL, "password": TEST_PASSWORD}
        )
        client_a = _auth_client(url, anon_key, session_a.session.access_token)

        rows_a = client_a.table("products").select("*").eq("id", product_id).execute()
        assert len(rows_a.data) == 1
        assert rows_a.data[0]["title"] == "RLS smoke product"

    finally:
        for uid in (user_a_id, user_b_id):
            if uid:
                try:
                    admin.auth.admin.delete_user(uid)
                except Exception:
                    pass
