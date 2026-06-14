#!/usr/bin/env python3
"""Trigger the daily digest job on the deployed backend (T3.6)."""

from __future__ import annotations

import json
import os
import sys
import time

import httpx

SEND_DIGESTS_PATH = "/internal/jobs/send-digests"
DEPLOY_WAIT_MAX_SECONDS = 600
DEPLOY_POLL_INTERVAL_SECONDS = 15


def _endpoint_available(base_url: str, client: httpx.Client) -> bool:
    try:
        response = client.get(f"{base_url}/openapi.json", timeout=30.0)
    except httpx.HTTPError:
        return False
    if response.status_code != 200:
        return False
    try:
        paths = response.json().get("paths", {})
    except json.JSONDecodeError:
        return False
    return SEND_DIGESTS_PATH in paths


def wait_for_deploy(base_url: str, client: httpx.Client) -> bool:
    """Poll until the send-digests route is registered on the deployed backend."""
    deadline = time.monotonic() + DEPLOY_WAIT_MAX_SECONDS
    while time.monotonic() < deadline:
        if _endpoint_available(base_url, client):
            return True
        time.sleep(DEPLOY_POLL_INTERVAL_SECONDS)
    return False


def main() -> int:
    base_url = os.environ.get("BACKEND_BASE_URL", "").rstrip("/")
    worker_token = os.environ.get("WORKER_TOKEN", "")
    if not base_url or not worker_token:
        print("BACKEND_BASE_URL and WORKER_TOKEN are required", file=sys.stderr)
        return 1

    url = f"{base_url}{SEND_DIGESTS_PATH}"
    with httpx.Client() as client:
        if not _endpoint_available(base_url, client):
            print(
                f"Waiting up to {DEPLOY_WAIT_MAX_SECONDS}s for {SEND_DIGESTS_PATH} "
                f"on {base_url} (Render deploy may still be in progress)...",
                file=sys.stderr,
            )
            if not wait_for_deploy(base_url, client):
                print(
                    f"Timed out waiting for {SEND_DIGESTS_PATH} on {base_url}. "
                    "Confirm Render auto-deploy from main completed and "
                    "BACKEND_BASE_URL points at the backend service (not the Vercel frontend).",
                    file=sys.stderr,
                )
                return 1

        try:
            response = client.post(
                url,
                headers={"X-Worker-Token": worker_token},
                timeout=600.0,
            )
        except httpx.HTTPError as exc:
            print(f"Request failed: {exc}", file=sys.stderr)
            return 1

    if response.status_code >= 400:
        print(
            f"HTTP {response.status_code} for POST {url}: {response.text}",
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
