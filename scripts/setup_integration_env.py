#!/usr/bin/env python3
"""Write backend/.env for integration tests from env vars or Supabase Management API."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / "backend" / ".env"
EXAMPLE_PATH = ROOT / "backend" / ".env.example"
BACKEND_ROOT = ROOT / "backend"

REQUIRED = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY")

sys.path.insert(0, str(BACKEND_ROOT))
from integration_env import (  # noqa: E402
    SETUP_HINT,
    is_placeholder_value,
    missing_or_placeholder_credentials,
)


def _strip(name: str) -> str:
    return (os.getenv(name) or "").strip()


def _load_example_defaults() -> dict[str, str]:
    if not EXAMPLE_PATH.exists():
        return {}
    values: dict[str, str] = {}
    for line in EXAMPLE_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _fetch_keys_from_management_api(token: str, project_ref: str) -> dict[str, str]:
    url = (
        f"https://api.supabase.com/v1/projects/{project_ref}/api-keys?reveal=true"
    )
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)

    anon_key = ""
    service_key = ""
    for entry in payload:
        name = (entry.get("name") or "").lower()
        key_type = (entry.get("type") or "").lower()
        api_key = entry.get("api_key") or ""
        if key_type in {"publishable", "anon"} or name == "anon":
            anon_key = api_key
        if key_type == "secret" or name in {"service_role", "service"}:
            service_key = api_key

    if not anon_key or not service_key:
        raise RuntimeError(
            "Management API response missing publishable/anon or secret/service_role keys"
        )

    return {
        "SUPABASE_URL": f"https://{project_ref}.supabase.co",
        "SUPABASE_ANON_KEY": anon_key,
        "SUPABASE_SERVICE_ROLE_KEY": service_key,
    }


def resolve_supabase_env() -> dict[str, str]:
    values = {name: _strip(name) for name in REQUIRED}

    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key in REQUIRED and value.strip():
                values[key] = value.strip()

    for name in REQUIRED:
        env_value = _strip(name)
        if env_value:
            values[name] = env_value

    if not missing_or_placeholder_credentials(values):
        return values

    token = _strip("SUPABASE_ACCESS_TOKEN") or _strip("SUPABASE_PAT")
    project_ref = _strip("SUPABASE_PROJECT_REF")
    if token and project_ref:
        return _fetch_keys_from_management_api(token, project_ref)

    return values


def write_backend_env(values: dict[str, str]) -> None:
    base = _load_example_defaults()
    for key, value in values.items():
        if key in REQUIRED and not is_placeholder_value(key, value):
            base[key] = value
    lines = [f"{key}={base[key]}" for key in sorted(base)]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    values = resolve_supabase_env()
    missing = missing_or_placeholder_credentials(values)
    if missing:
        print(
            f"ERROR: {SETUP_HINT}\n"
            "Provide either:\n"
            "  - SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY\n"
            "  - SUPABASE_ACCESS_TOKEN (or SUPABASE_PAT) + SUPABASE_PROJECT_REF\n"
            "via Cursor Cloud Secrets, shell env, or backend/.env.",
            file=sys.stderr,
        )
        print(f"Missing or placeholder: {', '.join(missing)}", file=sys.stderr)
        return 1

    write_backend_env(values)
    print(f"Wrote {ENV_PATH} for integration tests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
