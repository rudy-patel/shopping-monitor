"""Worker token dependency unit tests."""

from __future__ import annotations

import os

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from core.security import require_worker_token
from core.settings import clear_settings_cache


def make_app() -> FastAPI:
    app = FastAPI()

    @app.get("/internal/ping")
    async def ping(_: None = Depends(require_worker_token)):
        return {"ok": True}

    return app


@pytest.fixture
def worker_env(monkeypatch):
    snapshot = dict(os.environ)
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    clear_settings_cache()
    yield monkeypatch
    os.environ.clear()
    os.environ.update(snapshot)
    clear_settings_cache()


def test_worker_token_unconfigured_returns_503(worker_env, monkeypatch):
    monkeypatch.setenv("WORKER_TOKEN", "")
    clear_settings_cache()
    client = TestClient(make_app())

    response = client.get("/internal/ping")
    assert response.status_code == 503


def test_worker_token_missing_header_returns_401(worker_env, monkeypatch):
    monkeypatch.setenv("WORKER_TOKEN", "abc")
    clear_settings_cache()
    client = TestClient(make_app())

    response = client.get("/internal/ping")
    assert response.status_code == 401


def test_worker_token_wrong_value_returns_401(worker_env, monkeypatch):
    monkeypatch.setenv("WORKER_TOKEN", "abc")
    clear_settings_cache()
    client = TestClient(make_app())

    response = client.get("/internal/ping", headers={"X-Worker-Token": "xyz"})
    assert response.status_code == 401


def test_worker_token_correct_value_returns_200(worker_env, monkeypatch):
    monkeypatch.setenv("WORKER_TOKEN", "abc")
    clear_settings_cache()
    client = TestClient(make_app())

    response = client.get("/internal/ping", headers={"X-Worker-Token": "abc"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}
