#!/usr/bin/env python3
"""Apply a backend/db/migrations/*.sql file to the linked Supabase project.

Uses the Supabase Management API (requires SUPABASE_ACCESS_TOKEN or SUPABASE_PAT).
Service-role keys cannot run DDL; use MCP apply_migration or this script instead.

Usage:
  export SUPABASE_ACCESS_TOKEN=sbp_...
  export SUPABASE_URL=https://<project-ref>.supabase.co   # or SUPABASE_PROJECT_REF
  python scripts/apply_supabase_migration.py 002_scrape_job_advisory_lock.sql
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "backend" / "db" / "migrations"
BACKEND_ENV = ROOT / "backend" / ".env"


def _load_dotenv() -> None:
    if not BACKEND_ENV.is_file():
        return
    for line in BACKEND_ENV.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


def _project_ref() -> str:
    explicit = (os.getenv("SUPABASE_PROJECT_REF") or "").strip()
    if explicit:
        return explicit
    url = (os.getenv("SUPABASE_URL") or "").strip()
    match = re.search(r"https://([^.]+)\.supabase\.co", url)
    if match:
        return match.group(1)
    raise SystemExit(
        "Set SUPABASE_PROJECT_REF or SUPABASE_URL (https://<ref>.supabase.co)."
    )


def _access_token() -> str:
    token = (os.getenv("SUPABASE_ACCESS_TOKEN") or os.getenv("SUPABASE_PAT") or "").strip()
    if not token:
        raise SystemExit(
            "Set SUPABASE_ACCESS_TOKEN (or SUPABASE_PAT). "
            "Create one at https://supabase.com/dashboard/account/tokens "
            "or authenticate Supabase MCP in Cursor (Settings → Tools & MCP)."
        )
    return token


def _migration_path(name: str) -> Path:
    filename = name if name.endswith(".sql") else f"{name}.sql"
    path = MIGRATIONS_DIR / filename
    if not path.is_file():
        raise SystemExit(f"Migration not found: {path}")
    return path


def apply_migration(filename: str) -> None:
    path = _migration_path(filename)
    migration_name = path.stem
    sql = path.read_text(encoding="utf-8")
    project_ref = _project_ref()
    token = _access_token()

    body = json.dumps({"query": sql, "name": migration_name}).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{project_ref}/database/migrations",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "shopping-monitor-apply-migration/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            status = response.status
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Migration API failed ({exc.code}): {detail}") from exc

    print(f"Applied {filename} to project {project_ref} (HTTP {status}).")
    if payload.strip():
        print(payload)


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print(__doc__.strip(), file=sys.stderr)
        return 1
    apply_migration(args[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
