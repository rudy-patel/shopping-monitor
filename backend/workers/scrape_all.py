#!/usr/bin/env python3
"""Trigger the scheduled scrape-all job on the deployed backend (T3.5)."""

from __future__ import annotations

import json
import os
import sys

import httpx


def main() -> int:
    base_url = os.environ.get("BACKEND_BASE_URL", "").rstrip("/")
    worker_token = os.environ.get("WORKER_TOKEN", "")
    if not base_url or not worker_token:
        print("BACKEND_BASE_URL and WORKER_TOKEN are required", file=sys.stderr)
        return 1

    url = f"{base_url}/internal/jobs/scrape-all"
    try:
        response = httpx.post(
            url,
            headers={"X-Worker-Token": worker_token},
            timeout=600.0,
        )
    except httpx.HTTPError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    if response.status_code >= 400:
        print(
            f"HTTP {response.status_code}: {response.text}",
            file=sys.stderr,
        )
        return 1

    try:
        payload = response.json()
    except json.JSONDecodeError:
        print(response.text)
        return 0

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
