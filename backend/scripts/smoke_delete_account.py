"""Manual live account-delete smoke. NOT run in CI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import scrapers.bootstrap  # noqa: E402, F401
from fastapi.testclient import TestClient  # noqa: E402
from core.settings import clear_settings_cache  # noqa: E402
from main import app  # noqa: E402
from test.disposable_users import (  # noqa: E402
    DISPOSABLE_EMAIL_DOMAIN,
    DISPOSABLE_EMAIL_PREFIX,
    assert_safe_to_delete,
    disposable_email,
)

TEST_PASSWORD = "delete-account-smoke-password-32chars!"


def _service_client(url: str, service_key: str):
    from supabase import create_client

    return create_client(url, service_key)


def _anon_client(url: str, anon_key: str):
    from supabase import create_client

    return create_client(url, anon_key)


def _cleanup_disposable_users(admin) -> None:
    prefix = DISPOSABLE_EMAIL_PREFIX
    domain = f"@{DISPOSABLE_EMAIL_DOMAIN}"
    for user in admin.auth.admin.list_users(per_page=200):
        email = getattr(user, "email", None)
        user_id = getattr(user, "id", None)
        if not email or not user_id:
            continue
        if email.startswith(prefix) and email.endswith(domain):
            assert_safe_to_delete(user_id=user_id, email=email)
            admin.auth.admin.delete_user(user_id)


def _steps() -> list[str]:
    return [
        "cleanup prior delete-account-* disposable users",
        "create disposable user via admin API",
        "seed profiles row",
        "sign in with password and obtain JWT",
        "DELETE /api/account with AUTH_BYPASS_ENABLED=false",
        "verify auth user and profile rows are gone",
    ]


def main() -> int:
    if sys.version_info < (3, 12):
        print(
            "Python 3.12+ is required for the backend. "
            f"Current interpreter: {sys.version.split()[0]}",
            file=sys.stderr,
        )
        return 1

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run against local Supabase (requires credentials). Never use in CI.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required with --live to prevent accidental runs.",
    )
    args = parser.parse_args()

    if os.environ.get("CI", "").lower() in {"1", "true", "yes"} and args.live:
        print("Refusing --live account-delete smoke in CI.", file=sys.stderr)
        return 1

    if not args.live:
        print(json.dumps({"mode": "dry_run", "steps": _steps()}, indent=2))
        return 0

    if not args.confirm:
        print("--confirm is required with --live.", file=sys.stderr)
        return 1

    from integration_env import load_backend_dotenv, missing_or_placeholder_credentials

    load_backend_dotenv()
    missing = missing_or_placeholder_credentials()
    if missing:
        print(
            f"Missing Supabase credentials: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1

    url = os.environ["SUPABASE_URL"]
    anon_key = os.environ["SUPABASE_ANON_KEY"]
    service_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    admin = _service_client(url, service_key)
    anon = _anon_client(url, anon_key)
    email = disposable_email()
    user_id: str | None = None

    os.environ["AUTH_BYPASS_ENABLED"] = "false"
    os.environ["SCRAPER_MODE"] = "fixtures"
    clear_settings_cache()

    try:
        _cleanup_disposable_users(admin)
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
        assert response.status_code == 204, response.text

        try:
            admin.auth.admin.get_user_by_id(user_id)
            print("Auth user still exists after delete.", file=sys.stderr)
            return 1
        except Exception:
            pass

        profile_rows = admin.table("profiles").select("*").eq("user_id", user_id).execute()
        if profile_rows.data:
            print("Profile row still exists after delete.", file=sys.stderr)
            return 1

        print(json.dumps({"mode": "live", "email": email, "user_id": user_id, "status": "ok"}))
        user_id = None
        return 0
    finally:
        if user_id is not None:
            assert_safe_to_delete(user_id=user_id, email=email)
            try:
                admin.auth.admin.delete_user(user_id)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
