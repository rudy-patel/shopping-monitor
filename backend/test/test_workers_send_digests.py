"""Worker script unit tests for send-digests trigger."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import httpx

WORKER_SCRIPT = Path(__file__).resolve().parents[1] / "workers" / "send_digests.py"


def _load_worker_module(name: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, WORKER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_worker_missing_env_exits_1(monkeypatch):
    monkeypatch.delenv("BACKEND_BASE_URL", raising=False)
    monkeypatch.delenv("WORKER_TOKEN", raising=False)

    result = subprocess.run(
        [sys.executable, str(WORKER_SCRIPT)],
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if k not in {"BACKEND_BASE_URL", "WORKER_TOKEN"}},
    )

    assert result.returncode == 1
    assert "BACKEND_BASE_URL and WORKER_TOKEN are required" in result.stderr


def test_worker_success_prints_json(monkeypatch, capsys):
    monkeypatch.setenv("BACKEND_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("WORKER_TOKEN", "secret")

    post_response = MagicMock()
    post_response.status_code = 200
    post_response.json.return_value = {
        "mail_provider": "resend",
        "users_emailed": 1,
    }
    post_response.text = json.dumps(post_response.json.return_value)

    client = MagicMock()
    client.post.return_value = post_response
    client.__enter__.return_value = client
    client.__exit__.return_value = False

    module = _load_worker_module("send_digests_worker")
    monkeypatch.setattr(module, "_endpoint_available", lambda base_url, client: True)
    monkeypatch.setattr(module.httpx, "Client", lambda: client)

    assert module.main() == 0
    captured = capsys.readouterr()
    assert '"users_emailed": 1' in captured.out


def test_worker_http_error_exits_1(monkeypatch):
    monkeypatch.setenv("BACKEND_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("WORKER_TOKEN", "secret")

    post_response = MagicMock()
    post_response.status_code = 500
    post_response.text = "internal error"

    client = MagicMock()
    client.post.return_value = post_response
    client.__enter__.return_value = client
    client.__exit__.return_value = False

    module = _load_worker_module("send_digests_worker_err")
    monkeypatch.setattr(module, "_endpoint_available", lambda base_url, client: True)
    monkeypatch.setattr(module.httpx, "Client", lambda: client)

    assert module.main() == 1


def test_worker_network_error_exits_1(monkeypatch):
    monkeypatch.setenv("BACKEND_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("WORKER_TOKEN", "secret")

    client = MagicMock()
    client.post.side_effect = httpx.ConnectError("connection refused")
    client.__enter__.return_value = client
    client.__exit__.return_value = False

    module = _load_worker_module("send_digests_worker_net")
    monkeypatch.setattr(module, "_endpoint_available", lambda base_url, client: True)
    monkeypatch.setattr(module.httpx, "Client", lambda: client)

    assert module.main() == 1
