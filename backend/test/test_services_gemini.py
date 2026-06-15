"""GeminiFlashLlmProvider and factory wiring tests."""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors as genai_errors

from core.settings import Settings, clear_settings_cache
from services.categorizer import CategorizationContext
from services.factory import build_retailer_default_categories, get_categorizer, get_llm_provider
from services.gemini import GeminiFlashLlmProvider, _extract_json_text
from services.llm import (
    LlmCategorizationResult,
    LlmInvalidResponseError,
    LlmProviderError,
    LlmQuotaExhaustedError,
    LlmTimeoutError,
    NoOpLlmProvider,
)


def _make_provider(**kwargs) -> GeminiFlashLlmProvider:
    defaults = {
        "api_key": "test-key",
        "model": "gemini-2.5-flash",
        "default_timeout_s": 1.5,
        "discover_timeout_s": 30.0,
        "search_timeout_s": 5.0,
    }
    defaults.update(kwargs)
    return GeminiFlashLlmProvider(**defaults)


def _mock_response(text: str) -> MagicMock:
    response = MagicMock()
    response.text = text
    return response


@patch("services.gemini.genai.Client")
def test_categorize_valid_json(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        '{"category":"tech"}'
    )

    result = _make_provider().categorize(
        title="Sony WH-1000XM5",
        brand="Sony",
        retailer_slug="bestbuy_ca",
        breadcrumbs=["Electronics", "Headphones"],
    )

    assert result == LlmCategorizationResult(
        category="tech",
        raw_response='{"category":"tech"}',
    )


@patch("services.gemini.genai.Client")
def test_categorize_invalid_slug(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        '{"category":"gadgets"}'
    )

    with pytest.raises(LlmInvalidResponseError, match="invalid category slug"):
        _make_provider().categorize(
            title="Widget",
            brand=None,
            retailer_slug="bestbuy_ca",
            breadcrumbs=[],
        )


@patch("services.gemini.genai.Client")
def test_categorize_malformed_json(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response("not json")

    with pytest.raises(LlmInvalidResponseError, match="not valid JSON"):
        _make_provider().categorize(
            title="Widget",
            brand=None,
            retailer_slug="bestbuy_ca",
            breadcrumbs=[],
        )


@patch("services.gemini.genai.Client")
def test_categorize_timeout(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    def slow_generate_content(**_kwargs):
        time.sleep(0.2)
        return _mock_response('{"category":"tech"}')

    mock_client.models.generate_content.side_effect = slow_generate_content

    with pytest.raises(LlmTimeoutError, match="timed out after"):
        _make_provider().categorize(
            title="Widget",
            brand=None,
            retailer_slug="bestbuy_ca",
            breadcrumbs=[],
            timeout_s=0.05,
        )


@patch("services.gemini.genai.Client")
def test_categorize_quota_error(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.side_effect = genai_errors.APIError(
        429,
        {"error": {"status": "RESOURCE_EXHAUSTED", "message": "quota exceeded"}},
    )

    with pytest.raises(LlmQuotaExhaustedError):
        _make_provider().categorize(
            title="Widget",
            brand=None,
            retailer_slug="bestbuy_ca",
            breadcrumbs=[],
        )


def test_gemini_provider_raises_on_empty_api_key():
    with pytest.raises(LlmQuotaExhaustedError, match="GEMINI_API_KEY not configured"):
        GeminiFlashLlmProvider(api_key="", model="gemini-2.5-flash")


@patch("services.gemini.genai.Client")
def test_categorize_empty_response(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response("")

    with pytest.raises(LlmInvalidResponseError, match="empty categorization response"):
        _make_provider().categorize(
            title="Widget",
            brand=None,
            retailer_slug="bestbuy_ca",
            breadcrumbs=[],
        )


@patch("services.gemini.genai.Client")
def test_categorize_other_api_error_maps_to_provider_error(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.side_effect = genai_errors.APIError(
        500,
        {"error": {"status": "INTERNAL", "message": "server error"}},
    )

    with pytest.raises(LlmProviderError, match="500"):
        _make_provider().categorize(
            title="Widget",
            brand=None,
            retailer_slug="bestbuy_ca",
            breadcrumbs=[],
        )


@patch("services.gemini.genai.Client")
def test_discover_valid_json(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        '{"candidates":[{"url":"https://fixtures.local/bestbuy_ca/in_stock","justification":"same product"}]}'
    )

    from scrapers.bestbuy_ca import register_bestbuy_ca
    from scrapers.generic import register_generic

    register_generic()
    register_bestbuy_ca()

    result = _make_provider().discover(
        title="Lenovo Yoga Slim 7x",
        brand="Lenovo",
        retailer_slug="bestbuy_ca",
        variant_attributes={},
        image_url=None,
    )

    assert len(result.candidates) == 1
    assert str(result.candidates[0].url).endswith("bestbuy_ca/in_stock")


@patch("services.gemini.genai.Client")
def test_discover_filters_generic(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        '{"candidates":[{"url":"https://fixtures.local/generic/in_stock","justification":"generic"}]}'
    )

    from scrapers.generic import register_generic

    register_generic()

    result = _make_provider().discover(
        title="USB-C Hub",
        brand=None,
        retailer_slug="bestbuy_ca",
        variant_attributes={},
        image_url=None,
    )

    assert result.candidates == []


@patch("services.gemini.genai.Client")
def test_discover_rejects_more_than_eight(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    candidates = [
        {"url": f"https://example-{i}.ca/p", "justification": "match"}
        for i in range(9)
    ]
    mock_client.models.generate_content.return_value = _mock_response(
        json.dumps({"candidates": candidates})
    )

    with pytest.raises(LlmInvalidResponseError, match="more than 8"):
        _make_provider().discover(
            title="Widget",
            brand=None,
            retailer_slug="bestbuy_ca",
            variant_attributes={},
            image_url=None,
        )


@patch("services.gemini.genai.Client")
def test_discover_timeout(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    def slow_generate_content(**_kwargs):
        time.sleep(0.2)
        return _mock_response('{"candidates":[]}')

    mock_client.models.generate_content.side_effect = slow_generate_content

    with pytest.raises(LlmTimeoutError, match="discover timed out"):
        _make_provider(discover_timeout_s=0.05).discover(
            title="Widget",
            brand=None,
            retailer_slug="bestbuy_ca",
            variant_attributes={},
            image_url=None,
            timeout_s=0.05,
        )


@patch("services.gemini.genai.Client")
def test_discover_quota_error(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.side_effect = genai_errors.APIError(
        429,
        {"error": {"status": "RESOURCE_EXHAUSTED", "message": "quota exceeded"}},
    )

    with pytest.raises(LlmQuotaExhaustedError):
        _make_provider().discover(
            title="Widget",
            brand=None,
            retailer_slug="bestbuy_ca",
            variant_attributes={},
            image_url=None,
        )


@patch("services.gemini.genai.Client")
def test_discover_grounded_call_omits_structured_output_config(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        '{"candidates":[{"url":"https://fixtures.local/bestbuy_ca/in_stock","justification":"same product"}]}'
    )

    from scrapers.bestbuy_ca import register_bestbuy_ca
    from scrapers.generic import register_generic

    register_generic()
    register_bestbuy_ca()

    _make_provider().discover(
        title="Lenovo Yoga Slim 7x",
        brand="Lenovo",
        retailer_slug="bestbuy_ca",
        variant_attributes={},
        image_url=None,
    )

    config = mock_client.models.generate_content.call_args.kwargs["config"]
    assert config.tools is not None
    assert config.response_mime_type is None
    assert config.response_schema is None


def test_extract_json_text_strips_markdown_fence():
    fenced = '```json\n{"candidates":[]}\n```'
    assert _extract_json_text(fenced) == '{"candidates":[]}'


@patch("services.gemini.genai.Client")
def test_search_grounded_call_omits_structured_output_config(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        json.dumps(
            {
                "candidates": [
                    {
                        "url": "https://www.bestbuy.ca/en-ca/product/widget/12345",
                        "title": "Widget Pro",
                        "retailer_hint": "Best Buy Canada",
                        "brand_hint": "WidgetCo",
                        "justification": "Best Buy Canada PDP for the Widget Pro",
                    }
                ]
            }
        )
    )

    _make_provider().search(query="widget pro")

    config = mock_client.models.generate_content.call_args.kwargs["config"]
    assert config.tools is not None
    assert config.response_mime_type is None
    assert config.response_schema is None


@patch("services.gemini.genai.Client")
def test_search_parses_markdown_fenced_json(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        """```json
{"candidates":[{"url":"https://www.bestbuy.ca/en-ca/product/widget/12345","title":"Widget Pro","retailer_hint":"Best Buy Canada","brand_hint":"WidgetCo","justification":"match"}]}
```"""
    )

    result = _make_provider().search(query="widget pro")
    assert len(result.candidates) == 1
    assert result.candidates[0].title == "Widget Pro"


@patch("services.gemini.genai.Client")
def test_search_valid_json(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        json.dumps(
            {
                "candidates": [
                    {
                        "url": "https://www.bestbuy.ca/en-ca/product/widget/12345",
                        "title": "Widget Pro",
                        "retailer_hint": "Best Buy Canada",
                        "brand_hint": "WidgetCo",
                        "justification": "Best Buy Canada PDP for the Widget Pro",
                    }
                ]
            }
        )
    )

    result = _make_provider().search(query="widget pro")
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.title == "Widget Pro"
    assert candidate.retailer_hint == "Best Buy Canada"
    assert candidate.brand_hint == "WidgetCo"


@patch("services.gemini.genai.Client")
def test_search_skips_invalid_candidate(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        json.dumps(
            {
                "candidates": [
                    {
                        "url": "not-a-url",
                        "title": "Bad",
                        "retailer_hint": None,
                        "brand_hint": None,
                        "justification": "bad",
                    },
                    {
                        "url": "https://www.indigo.ca/en-ca/p/good",
                        "title": "Good Product",
                        "retailer_hint": "Indigo",
                        "brand_hint": None,
                        "justification": "valid candidate",
                    },
                ]
            }
        )
    )

    result = _make_provider().search(query="something")
    assert len(result.candidates) == 1
    assert str(result.candidates[0].url).endswith("/p/good")


@patch("services.gemini.genai.Client")
def test_search_rejects_more_than_eight(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    candidates = [
        {
            "url": f"https://example-{i}.ca/p",
            "title": f"Product {i}",
            "retailer_hint": None,
            "brand_hint": None,
            "justification": "match",
        }
        for i in range(9)
    ]
    mock_client.models.generate_content.return_value = _mock_response(
        json.dumps({"candidates": candidates})
    )

    with pytest.raises(LlmInvalidResponseError, match="more than 8"):
        _make_provider().search(query="too many")


@patch("services.gemini.genai.Client")
def test_search_timeout(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    def slow_generate_content(**_kwargs):
        time.sleep(0.2)
        return _mock_response('{"candidates":[]}')

    mock_client.models.generate_content.side_effect = slow_generate_content

    with pytest.raises(LlmTimeoutError, match="search timed out"):
        _make_provider(search_timeout_s=0.05).search(query="something", timeout_s=0.05)


@patch("services.gemini.genai.Client")
def test_search_quota_error(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.side_effect = genai_errors.APIError(
        429,
        {"error": {"status": "RESOURCE_EXHAUSTED", "message": "quota"}},
    )

    with pytest.raises(LlmQuotaExhaustedError):
        _make_provider().search(query="something")


@patch("services.gemini.genai.Client")
def test_search_empty_response_raises(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response("")

    with pytest.raises(LlmInvalidResponseError, match="empty search response"):
        _make_provider().search(query="something")


def test_build_retailer_default_categories_includes_registered_retailers():
    defaults = build_retailer_default_categories()
    assert defaults["generic"] == "other"
    assert defaults["bestbuy_ca"] == "tech"
    assert defaults["palmisleskate"] == "other"
    assert defaults["tikiroomskate"] == "other"
    assert defaults["indigo"] == "other"
    assert defaults["apple_ca"] == "tech"
    assert defaults["abercrombie"] == "clothing"


def test_get_llm_provider_no_key_live_mode_returns_noop(monkeypatch):
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    clear_settings_cache()
    provider = get_llm_provider(Settings(gemini_api_key="", scraper_mode="live"))
    assert isinstance(provider, NoOpLlmProvider)


def test_get_llm_provider_no_key_fixtures_mode_returns_fixture_provider(monkeypatch):
    """T8.10: SCRAPER_MODE=fixtures swaps in FixtureLlmProvider so the search UI works
    without a Gemini API key (local dev, CI)."""
    from services.llm_fixtures import FixtureLlmProvider

    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    clear_settings_cache()
    provider = get_llm_provider(Settings(gemini_api_key="", scraper_mode="fixtures"))
    assert isinstance(provider, FixtureLlmProvider)


def test_get_llm_provider_with_key(monkeypatch):
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    clear_settings_cache()
    provider = get_llm_provider(Settings(gemini_api_key="secret"))
    assert isinstance(provider, GeminiFlashLlmProvider)


@patch("services.gemini.genai.Client")
def test_default_categorizer_gemini_fallback(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    def slow_generate_content(**_kwargs):
        time.sleep(0.2)
        return _mock_response('{"category":"tech"}')

    mock_client.models.generate_content.side_effect = slow_generate_content

    categorizer = get_categorizer(
        Settings(gemini_api_key="secret", gemini_categorize_timeout_s=0.05)
    )
    result = categorizer.categorize(
        CategorizationContext(
            title="Sony WH-1000XM5",
            brand="Sony",
            retailer_slug="unknown_retailer",
            breadcrumbs=["Electronics", "Headphones"],
        )
    )

    assert result.category == "tech"
    assert result.source == "heuristic"
