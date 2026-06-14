"""Worker script unit tests for scrape-all trigger."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import httpx

WORKER_SCRIPT = Path(__file__).resolve().parents[1] / "workers" / "scrape_all.py"


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

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"status": "completed", "listings_total": 1}
    response.text = json.dumps(response.json.return_value)

    monkeypatch.setattr(
        "httpx.post",
        lambda *args, **kwargs: response,
    )

    import importlib.util

    spec = importlib.util.spec_from_file_location("scrape_all_worker", WORKER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.main() == 0
    captured = capsys.readouterr()
    assert '"status": "completed"' in captured.out


def test_worker_http_error_exits_1(monkeypatch):
    monkeypatch.setenv("BACKEND_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("WORKER_TOKEN", "secret")

    response = MagicMock()
    response.status_code = 500
    response.text = "internal error"
    monkeypatch.setattr("httpx.post", lambda *args, **kwargs: response)

    import importlib.util

    spec = importlib.util.spec_from_file_location("scrape_all_worker_err", WORKER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.main() == 1


def test_worker_network_error_exits_1(monkeypatch):
    monkeypatch.setenv("BACKEND_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("WORKER_TOKEN", "secret")

    def raise_error(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("httpx.post", raise_error)

    import importlib.util

    spec = importlib.util.spec_from_file_location("scrape_all_worker_net", WORKER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.main() == 1
