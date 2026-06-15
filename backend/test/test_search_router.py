"""Search router unit tests (T8.2)."""

from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.settings import clear_settings_cache
from routers.search import get_search_client, router as search_router
from services.llm import (
    FakeLlmProvider,
    LlmInvalidResponseError,
    LlmQuotaExhaustedError,
    LlmSearchCandidate,
    LlmSearchResult,
    LlmTimeoutError,
)
from test.fake_supabase import FakeSupabaseClient


@pytest.fixture(autouse=True)
def _registry():
    """Bootstrap retailer registry; module-level import is unreliable when other
    tests reset the registry between cases."""
    from scrapers.bestbuy_ca import register_bestbuy_ca
    from scrapers.generic import register_generic
    from scrapers.indigo import register_indigo
    from scrapers.registry import reset_registry

    reset_registry()
    register_generic()
    register_bestbuy_ca()
    register_indigo()
    yield
    reset_registry()


def make_app(fake_llm: FakeLlmProvider) -> tuple[FastAPI, FakeSupabaseClient]:
    app = FastAPI()
    app.include_router(search_router)
    client = FakeSupabaseClient()
    app.dependency_overrides[get_search_client] = lambda: client
    # search_service.run_search resolves the LLM via get_llm_provider; we monkey-patch
    # that inside individual tests because dependency overrides only catch FastAPI deps.
    return app, client


@pytest.fixture
def auth_env(monkeypatch):
    snapshot = dict(os.environ)
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "true")
    monkeypatch.setenv("SCRAPER_MODE", "live")
    clear_settings_cache()
    yield monkeypatch
    os.environ.clear()
    os.environ.update(snapshot)
    clear_settings_cache()


def test_search_returns_classified_results(auth_env):
    llm = FakeLlmProvider(
        search_result=LlmSearchResult(
            candidates=[
                LlmSearchCandidate(
                    url="https://www.bestbuy.ca/en-ca/product/widget/12345",
                    title="Best Buy Widget",
                    retailer_hint="Best Buy Canada",
                    brand_hint="WidgetCo",
                    justification="Best Buy carries it",
                ),
                LlmSearchCandidate(
                    url="https://walmart.ca/en/ip/widget/2",
                    title="Walmart Widget",
                    retailer_hint="Walmart Canada",
                    brand_hint=None,
                    justification="Also carried at Walmart",
                ),
            ]
        )
    )
    app, _ = make_app(llm)
    auth_env.setattr("services.search_service.get_llm_provider", lambda: llm)

    with TestClient(app) as client:
        response = client.post("/api/search", json={"query": "widget"})

    assert response.status_code == 200
    body = response.json()
    assert body["cache_hit"] is False
    assert len(body["results"]) == 2
    assert body["results"][0]["supported"] is True
    assert body["results"][0]["retailer_slug"] == "bestbuy_ca"
    assert body["results"][1]["supported"] is False


def test_search_returns_cached_response_on_second_call(auth_env):
    llm = FakeLlmProvider(
        search_result=LlmSearchResult(
            candidates=[
                LlmSearchCandidate(
                    url="https://www.bestbuy.ca/en-ca/product/widget/1",
                    title="Widget",
                    retailer_hint=None,
                    brand_hint=None,
                    justification="match",
                )
            ]
        )
    )
    app, _ = make_app(llm)
    auth_env.setattr("services.search_service.get_llm_provider", lambda: llm)

    with TestClient(app) as client:
        first = client.post("/api/search", json={"query": "widget"})
        second = client.post("/api/search", json={"query": "widget"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["cache_hit"] is False
    assert second.json()["cache_hit"] is True
    assert len(llm.search_calls) == 1


def test_search_quota_exhausted_returns_503(auth_env):
    llm = FakeLlmProvider(raise_on_search=LlmQuotaExhaustedError("rate limit"))
    app, _ = make_app(llm)
    auth_env.setattr("services.search_service.get_llm_provider", lambda: llm)

    with TestClient(app) as client:
        response = client.post("/api/search", json={"query": "widget"})

    assert response.status_code == 503


def test_search_timeout_returns_504(auth_env):
    llm = FakeLlmProvider(raise_on_search=LlmTimeoutError("too slow"))
    app, _ = make_app(llm)
    auth_env.setattr("services.search_service.get_llm_provider", lambda: llm)

    with TestClient(app) as client:
        response = client.post("/api/search", json={"query": "widget"})

    assert response.status_code == 504


def test_search_invalid_response_returns_502(auth_env):
    llm = FakeLlmProvider(raise_on_search=LlmInvalidResponseError("bad json"))
    app, _ = make_app(llm)
    auth_env.setattr("services.search_service.get_llm_provider", lambda: llm)

    with TestClient(app) as client:
        response = client.post("/api/search", json={"query": "widget"})

    assert response.status_code == 502


def test_search_short_query_returns_422(auth_env):
    llm = FakeLlmProvider()
    app, _ = make_app(llm)
    auth_env.setattr("services.search_service.get_llm_provider", lambda: llm)

    with TestClient(app) as client:
        response = client.post("/api/search", json={"query": "x"})

    assert response.status_code == 422


def test_search_empty_results_returns_200(auth_env):
    llm = FakeLlmProvider(search_result=LlmSearchResult(candidates=[]))
    app, _ = make_app(llm)
    auth_env.setattr("services.search_service.get_llm_provider", lambda: llm)

    with TestClient(app) as client:
        response = client.post("/api/search", json={"query": "obscure"})

    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
