"""T6.2 production smoke: live add + refresh on Render for multiple retailers.

NOT run in CI. Uses disposable Supabase users and production API only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import httpx  # noqa: E402

from core.protected_accounts import DISPOSABLE_EMAIL_DOMAIN  # noqa: E402
from scripts.production_smoke_helpers import (  # noqa: E402
    RETAILERS,
    summarize_add_result,
    validate_add_response,
)

PROD_API_DEFAULT = "https://shopping-monitor-api.onrender.com"
SMOKE_EMAIL_PREFIX = "smoke-t62-"
TEST_PASSWORD = "smoke-t62-password-32chars!!!!"


def _service_client(url: str, service_key: str):
    from supabase import create_client

    return create_client(url, service_key)


def _anon_client(url: str, anon_key: str):
    from supabase import create_client

    return create_client(url, anon_key)


def disposable_email() -> str:
    return f"{SMOKE_EMAIL_PREFIX}{uuid4()}@{DISPOSABLE_EMAIL_DOMAIN}"


def _cleanup_smoke_users(admin) -> None:
    suffix = f"@{DISPOSABLE_EMAIL_DOMAIN}"
    for user in admin.auth.admin.list_users(per_page=200):
        email = getattr(user, "email", None)
        user_id = getattr(user, "id", None)
        if not email or not user_id:
            continue
        if email.startswith(SMOKE_EMAIL_PREFIX) and email.endswith(suffix):
            admin.auth.admin.delete_user(user_id)


def _create_session(admin, anon, *, email: str) -> tuple[str, str]:
    created = admin.auth.admin.create_user(
        {"email": email, "password": TEST_PASSWORD, "email_confirm": True}
    )
    user_id = created.user.id
    admin.table("profiles").insert({"user_id": user_id}).execute()
    session = anon.auth.sign_in_with_password({"email": email, "password": TEST_PASSWORD})
    token = session.session.access_token
    return user_id, token


def _add_product(
    client: httpx.Client,
    *,
    prod_api: str,
    token: str,
    url: str,
    expected_retailer: str,
    max_seconds: float,
) -> tuple[dict, float]:
    started = time.perf_counter()
    response = client.post(
        f"{prod_api}/api/products",
        json={"url": url, "category": "auto"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=120.0,
    )
    elapsed = time.perf_counter() - started
    if response.status_code != 201:
        raise RuntimeError(f"add failed {response.status_code}: {response.text}")
    body = response.json()
    validate_add_response(
        body,
        expected_retailer=expected_retailer,
        max_seconds=max_seconds,
        elapsed=elapsed,
    )
    return body, elapsed


def _refresh_product(
    client: httpx.Client,
    *,
    prod_api: str,
    token: str,
    product_id: str,
) -> int:
    response = client.post(
        f"{prod_api}/api/products/{product_id}/refresh",
        headers={"Authorization": f"Bearer {token}"},
        timeout=120.0,
    )
    return response.status_code


def _delete_product(
    client: httpx.Client,
    *,
    prod_api: str,
    token: str,
    product_id: str,
) -> None:
    response = client.delete(
        f"{prod_api}/api/products/{product_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60.0,
    )
    if response.status_code != 204:
        raise RuntimeError(f"delete product failed {response.status_code}: {response.text}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prod-api", default=PROD_API_DEFAULT)
    parser.add_argument("--max-add-seconds", type=float, default=10.0)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run against production API (requires Supabase credentials).",
    )
    args = parser.parse_args()

    if os.environ.get("CI", "").lower() in {"1", "true", "yes"} and args.live:
        print("Refusing --live production smoke in CI.", file=sys.stderr)
        return 1

    if not args.live:
        print(
            json.dumps(
                {
                    "mode": "dry_run",
                    "prod_api": args.prod_api,
                    "retailers": list(RETAILERS),
                },
                indent=2,
            )
        )
        return 0

    from integration_env import load_backend_dotenv, missing_or_placeholder_credentials

    load_backend_dotenv()
    missing = missing_or_placeholder_credentials()
    if missing:
        print(f"Missing Supabase credentials: {', '.join(missing)}", file=sys.stderr)
        return 1

    url = os.environ["SUPABASE_URL"]
    anon_key = os.environ["SUPABASE_ANON_KEY"]
    service_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    admin = _service_client(url, service_key)
    anon = _anon_client(url, anon_key)
    email = disposable_email()
    user_id: str | None = None
    token: str | None = None
    product_ids: list[str] = []
    results: list[dict] = []

    try:
        _cleanup_smoke_users(admin)
        user_id, token = _create_session(admin, anon, email=email)

        with httpx.Client() as client:
            for retailer in RETAILERS:
                body, elapsed = _add_product(
                    client,
                    prod_api=args.prod_api,
                    token=token,
                    url=retailer["url"],
                    expected_retailer=retailer["slug"],
                    max_seconds=args.max_add_seconds,
                )
                product_id = str(body["id"])
                product_ids.append(product_id)
                refresh_status = _refresh_product(
                    client,
                    prod_api=args.prod_api,
                    token=token,
                    product_id=product_id,
                )
                results.append(
                    summarize_add_result(
                        body,
                        retailer=retailer["slug"],
                        url=retailer["url"],
                        elapsed=elapsed,
                        refresh_status=refresh_status,
                    )
                )

            for product_id in product_ids:
                _delete_product(
                    client,
                    prod_api=args.prod_api,
                    token=token,
                    product_id=product_id,
                )
            product_ids.clear()

        if user_id is not None:
            admin.auth.admin.delete_user(user_id)
            user_id = None

        print(json.dumps({"mode": "live", "email": email, "results": results}, indent=2))
        return 0
    finally:
        if token and product_ids:
            try:
                with httpx.Client() as client:
                    for product_id in product_ids:
                        _delete_product(
                            client,
                            prod_api=args.prod_api,
                            token=token,
                            product_id=product_id,
                        )
            except Exception:
                pass
        if user_id is not None:
            try:
                admin.auth.admin.delete_user(user_id)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
