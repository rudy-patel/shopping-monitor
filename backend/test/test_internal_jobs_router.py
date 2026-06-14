"""Internal jobs router unit tests."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from core.settings import clear_settings_cache
from main import app
from services.scrape_job_service import ScrapeAllResult


@pytest.fixture
def worker_env(monkeypatch):
    snapshot = dict(os.environ)
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    clear_settings_cache()
    yield monkeypatch
    os.environ.clear()
    os.environ.update(snapshot)
    clear_settings_cache()


def test_scrape_all_unconfigured_worker_token_returns_503(worker_env, monkeypatch):
    monkeypatch.setenv("WORKER_TOKEN", "")
    clear_settings_cache()
    client = TestClient(app)

    response = client.post("/internal/jobs/scrape-all")
    assert response.status_code == 503


def test_scrape_all_missing_token_returns_401(worker_env, monkeypatch):
    monkeypatch.setenv("WORKER_TOKEN", "secret")
    clear_settings_cache()
    client = TestClient(app)

    response = client.post("/internal/jobs/scrape-all")
    assert response.status_code == 401


def test_scrape_all_bad_token_returns_401(worker_env, monkeypatch):
    monkeypatch.setenv("WORKER_TOKEN", "secret")
    clear_settings_cache()
    client = TestClient(app)

    response = client.post(
        "/internal/jobs/scrape-all",
        headers={"X-Worker-Token": "wrong"},
    )
    assert response.status_code == 401


def test_scrape_all_happy_path(worker_env, monkeypatch):
    monkeypatch.setenv("WORKER_TOKEN", "secret")
    clear_settings_cache()

    expected = ScrapeAllResult(
        status="completed",
        reason=None,
        listings_total=2,
        listings_ok=2,
        listings_failed=0,
        success_rate=1.0,
        products_evaluated=1,
        users_revisit_evaluated=1,
        notifications_created=0,
        duration_seconds=1.2,
    )
    monkeypatch.setattr(
        "routers.internal_jobs.run_scrape_all",
        lambda client: expected,
    )
    monkeypatch.setattr(
        "routers.internal_jobs.get_service_role_client",
        lambda: object(),
    )

    client = TestClient(app)
    response = client.post(
        "/internal/jobs/scrape-all",
        headers={"X-Worker-Token": "secret"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["listings_total"] == 2


def test_send_digests_unconfigured_worker_token_returns_503(worker_env, monkeypatch):
    monkeypatch.setenv("WORKER_TOKEN", "")
    clear_settings_cache()
    client = TestClient(app)

    response = client.post("/internal/jobs/send-digests")
    assert response.status_code == 503


def test_send_digests_missing_token_returns_401(worker_env, monkeypatch):
    monkeypatch.setenv("WORKER_TOKEN", "secret")
    clear_settings_cache()
    client = TestClient(app)

    response = client.post("/internal/jobs/send-digests")
    assert response.status_code == 401


def test_send_digests_bad_token_returns_401(worker_env, monkeypatch):
    monkeypatch.setenv("WORKER_TOKEN", "secret")
    clear_settings_cache()
    client = TestClient(app)

    response = client.post(
        "/internal/jobs/send-digests",
        headers={"X-Worker-Token": "wrong"},
    )
    assert response.status_code == 401


def test_send_digests_happy_path(worker_env, monkeypatch):
    from services.digest_job_service import SendDigestsResult

    monkeypatch.setenv("WORKER_TOKEN", "secret")
    clear_settings_cache()

    expected = SendDigestsResult(
        mail_provider="resend",
        users_emailed=1,
        users_failed=0,
        users_skipped_no_unread=0,
        users_skipped_digest_disabled=0,
        users_skipped_no_email=0,
        notifications_marked_sent=2,
        duration_seconds=0.5,
    )
    monkeypatch.setattr(
        "routers.internal_jobs.run_send_digests",
        lambda client: expected,
    )
    monkeypatch.setattr(
        "routers.internal_jobs.get_service_role_client",
        lambda: object(),
    )

    client = TestClient(app)
    response = client.post(
        "/internal/jobs/send-digests",
        headers={"X-Worker-Token": "secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mail_provider"] == "resend"
    assert body["users_emailed"] == 1
    assert body["notifications_marked_sent"] == 2


def test_scrape_all_skipped_lock_returns_200(worker_env, monkeypatch):
    monkeypatch.setenv("WORKER_TOKEN", "secret")
    clear_settings_cache()

    skipped = ScrapeAllResult(
        status="skipped",
        reason="lock_not_acquired",
        listings_total=0,
        listings_ok=0,
        listings_failed=0,
        success_rate=0.0,
        products_evaluated=0,
        users_revisit_evaluated=0,
        notifications_created=0,
        duration_seconds=0.0,
    )
    monkeypatch.setattr(
        "routers.internal_jobs.run_scrape_all",
        lambda client: skipped,
    )
    monkeypatch.setattr(
        "routers.internal_jobs.get_service_role_client",
        lambda: object(),
    )

    client = TestClient(app)
    response = client.post(
        "/internal/jobs/scrape-all",
        headers={"X-Worker-Token": "secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "skipped"
    assert body["reason"] == "lock_not_acquired"
