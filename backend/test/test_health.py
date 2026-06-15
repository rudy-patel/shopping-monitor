"""Health endpoint unit tests."""

from fastapi.testclient import TestClient

from core.settings import (
    DEFAULT_GEMINI_DISCOVER_TIMEOUT_S,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GEMINI_SEARCH_MODEL,
    DEFAULT_GEMINI_SEARCH_TIMEOUT_S,
)
from main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "running" in response.json()["message"].lower()


def test_health_head():
    response = client.head("/health")
    assert response.status_code == 200


def test_health_get():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "shopping-monitor-api"
    assert body["status"] in ("healthy", "degraded")


def test_health_llm_returns_configured_models():
    """`/health/llm` must report wired Gemini config without calling Gemini.

    Production debugging hits this from a curl when search misbehaves; the contract
    is that it reveals model wiring + timeouts + scraper mode and never burns quota.
    """
    response = client.get("/health/llm")
    assert response.status_code == 200
    body = response.json()
    # Default test env has no GEMINI_API_KEY → configured=False.
    assert body["configured"] is False
    assert body["categorize_model"] == DEFAULT_GEMINI_MODEL
    assert body["search_model"] == DEFAULT_GEMINI_SEARCH_MODEL
    assert body["search_timeout_s"] == DEFAULT_GEMINI_SEARCH_TIMEOUT_S
    assert body["discover_timeout_s"] == DEFAULT_GEMINI_DISCOVER_TIMEOUT_S
    assert body["scraper_mode"] in ("fixtures", "live", "record")
    assert isinstance(body["checked_at"], int)
