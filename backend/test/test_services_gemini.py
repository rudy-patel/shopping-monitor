"""GeminiFlashLlmProvider and factory wiring tests."""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors as genai_errors

from core.settings import DEFAULT_GEMINI_SEARCH_TIMEOUT_S, Settings, clear_settings_cache
from services.categorizer import CategorizationContext
from services.factory import build_retailer_default_categories, get_categorizer, get_llm_provider
from services.gemini import (
    GeminiFlashLlmProvider,
    _extract_grounded_response_text,
    _extract_json_text,
)
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
        "search_model": "gemini-2.5-flash-lite",
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
        clean_title=None,
        raw_response='{"category":"tech"}',
    )


@patch("services.gemini.genai.Client")
def test_categorize_returns_clean_title(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    payload = (
        '{"category":"tech","clean_title":"Apple AirPods Pro 3"}'
    )
    mock_client.models.generate_content.return_value = _mock_response(payload)

    result = _make_provider().categorize(
        title=(
            "Apple AirPods Pro 3 Noise Cancelling True Wireless Earbuds with "
            "MagSafe Charging Case"
        ),
        brand="Apple",
        retailer_slug="bestbuy_ca",
        breadcrumbs=["Electronics", "Audio"],
    )

    assert result.category == "tech"
    assert result.clean_title == "Apple AirPods Pro 3"


@pytest.mark.parametrize(
    "raw_clean_title",
    [
        "",  # empty string
        "   ",  # whitespace only
        "abc",  # 3 chars (just below MIN_CLEAN_TITLE_LEN=4)
        "x" * 81,  # 81 chars (just above MAX_CLEAN_TITLE_LEN=80)
    ],
)
@patch("services.gemini.genai.Client")
def test_categorize_drops_invalid_clean_title(
    mock_client_cls: MagicMock, raw_clean_title: str
):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    payload = json.dumps({"category": "tech", "clean_title": raw_clean_title})
    mock_client.models.generate_content.return_value = _mock_response(payload)

    result = _make_provider().categorize(
        title="Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
        brand="Sony",
        retailer_slug="bestbuy_ca",
        breadcrumbs=["Electronics", "Audio"],
    )

    # Bad title is dropped silently; category is still trusted.
    assert result.category == "tech"
    assert result.clean_title is None


@pytest.mark.parametrize("raw_clean_title", ["abcd", "x" * 80])
@patch("services.gemini.genai.Client")
def test_categorize_accepts_clean_title_at_inclusive_length_bounds(
    mock_client_cls: MagicMock, raw_clean_title: str
):
    """Lock that MIN/MAX_CLEAN_TITLE_LEN are inclusive — guards against a future
    `<=`/`>=` slip that would silently drop boundary-valid titles."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    payload = json.dumps({"category": "tech", "clean_title": raw_clean_title})
    mock_client.models.generate_content.return_value = _mock_response(payload)

    result = _make_provider().categorize(
        title="Some long scraped product title that needs cleaning here",
        brand="Brand",
        retailer_slug="bestbuy_ca",
        breadcrumbs=[],
    )

    assert result.clean_title == raw_clean_title


@patch("services.gemini.genai.Client")
def test_categorize_clean_title_strips_whitespace(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        '{"category":"tech","clean_title":"  Apple AirPods Pro 3  "}'
    )

    result = _make_provider().categorize(
        title="Apple AirPods Pro 3 with Long SEO Suffix",
        brand="Apple",
        retailer_slug="bestbuy_ca",
        breadcrumbs=[],
    )

    assert result.clean_title == "Apple AirPods Pro 3"


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


def test_extract_grounded_response_text_falls_back_to_candidate_parts():
    part = MagicMock()
    part.text = '{"candidates":[]}'
    content = MagicMock()
    content.parts = [part]
    candidate = MagicMock()
    candidate.content = content
    response = MagicMock()
    response.text = None
    response.candidates = [candidate]
    assert _extract_grounded_response_text(response) == '{"candidates":[]}'


@patch("services.gemini.time.sleep")
@patch("services.gemini.genai.Client")
def test_grounded_search_does_not_retry_on_quota_error(
    mock_client_cls: MagicMock,
    mock_sleep: MagicMock,
):
    """Quota exhaustion is a daily cap — every retry burns more quota for the
    same wall-time wait. Fail fast so the frontend can surface the daily-limit
    message immediately instead of after multiple attempts."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.side_effect = genai_errors.APIError(
        429,
        {"error": {"status": "RESOURCE_EXHAUSTED", "message": "rate limit"}},
    )

    with pytest.raises(LlmQuotaExhaustedError):
        _make_provider().search(query="patagonia")

    assert mock_client.models.generate_content.call_count == 1
    mock_sleep.assert_not_called()


@patch("services.gemini.time.sleep")
@patch("services.gemini.genai.Client")
def test_grounded_search_retries_on_transient_503(
    mock_client_cls: MagicMock,
    mock_sleep: MagicMock,
):
    """503 UNAVAILABLE is a documented transient failure for Gemini grounded
    search (python-genai#2249). One retry typically clears it."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    unavailable = genai_errors.APIError(
        503,
        {"error": {"status": "UNAVAILABLE", "message": "model overloaded"}},
    )
    mock_client.models.generate_content.side_effect = [
        unavailable,
        _mock_response('{"candidates":[]}'),
    ]

    result = _make_provider().search(query="patagonia")

    assert result.candidates == []
    assert mock_client.models.generate_content.call_count == 2
    mock_sleep.assert_called_once()


@patch("services.gemini.time.sleep")
@patch("services.gemini.genai.Client")
def test_grounded_search_retries_on_transient_504(
    mock_client_cls: MagicMock,
    mock_sleep: MagicMock,
):
    """504 DEADLINE_EXCEEDED is the second most common grounded-search transient
    error (see capacity rotation reports in python-genai#2249)."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    deadline = genai_errors.APIError(
        504,
        {"error": {"status": "DEADLINE_EXCEEDED", "message": "grounded deadline"}},
    )
    mock_client.models.generate_content.side_effect = [
        deadline,
        _mock_response('{"candidates":[]}'),
    ]

    result = _make_provider().search(query="patagonia")

    assert result.candidates == []
    assert mock_client.models.generate_content.call_count == 2
    mock_sleep.assert_called_once()


@patch("services.gemini.time.sleep")
@patch("services.gemini.genai.Client")
def test_grounded_search_retries_on_empty_response(
    mock_client_cls: MagicMock,
    mock_sleep: MagicMock,
):
    """Empty grounded response (model returned no text despite running) is
    intermittent — retry once before failing."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.side_effect = [
        _mock_response(""),
        _mock_response('{"candidates":[]}'),
    ]

    result = _make_provider().search(query="patagonia")

    assert result.candidates == []
    assert mock_client.models.generate_content.call_count == 2


@patch("services.gemini.genai.Client")
def test_search_uses_search_model_not_default_model(mock_client_cls: MagicMock):
    """Grounded search uses `search_model` so production can run Flash for
    categorization and Flash-Lite for search (separate quota pools)."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        '{"candidates":[]}'
    )

    provider = _make_provider(
        model="gemini-2.5-flash",
        search_model="gemini-2.5-flash-lite",
    )
    provider.search(query="something")

    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-flash-lite"


@patch("services.gemini.genai.Client")
def test_search_model_falls_back_to_default_model(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        '{"candidates":[]}'
    )

    provider = _make_provider(model="gemini-2.5-flash", search_model=None)
    provider.search(query="something")

    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-flash"


@patch("services.gemini.genai.Client")
def test_discover_uses_search_model_not_categorize_model(mock_client_cls: MagicMock):
    """Discovery is a *grounded* call (google_search tool) just like search, so it
    must use the grounded-friendly `search_model` (Flash-Lite), not the structured-
    output `model` (Flash). Burning Flash quota on discover would re-trigger the
    daily-cap outage this PR fixed."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        '{"candidates":[]}'
    )

    from scrapers.bestbuy_ca import register_bestbuy_ca
    from scrapers.generic import register_generic

    register_generic()
    register_bestbuy_ca()

    provider = _make_provider(
        model="gemini-2.5-flash",
        search_model="gemini-2.5-flash-lite",
    )
    provider.discover(
        title="Widget",
        brand=None,
        retailer_slug="bestbuy_ca",
        variant_attributes={},
        image_url=None,
    )

    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-flash-lite"


@patch("services.gemini.time.sleep")
@patch("services.gemini.genai.Client")
def test_search_does_not_double_wrap_provider_error(
    mock_client_cls: MagicMock, mock_sleep: MagicMock
):
    """`_call_gemini_grounded` already classifies API errors into LlmProviderError;
    the outer search() / discover() wrappers must re-raise it cleanly instead of
    feeding it back through `_raise_gemini_call_error` (which would re-wrap it as
    `LlmProviderError(str(LlmProviderError(...)))` with a noisy message)."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    # Persistent 500 — no quota, no transient retry success → bubbles up as LlmProviderError
    # from `_call_gemini_grounded` after exhausting retries.
    mock_client.models.generate_content.side_effect = genai_errors.APIError(
        500,
        {"error": {"status": "INTERNAL", "message": "boom"}},
    )

    with pytest.raises(LlmProviderError) as exc_info:
        _make_provider().search(query="something")

    # The chain should be: APIError → LlmProviderError (once). The cause must be the
    # APIError, not another LlmProviderError (which would indicate double-wrap).
    assert not isinstance(exc_info.value.__cause__, LlmProviderError)
    # Should retry 500s (transient) then give up after _GROUNDED_MAX_ATTEMPTS.
    assert mock_client.models.generate_content.call_count == 3


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
def test_search_natural_language_refusal_returns_empty_results(
    mock_client_cls: MagicMock,
):
    """Gemini occasionally returns 'I'm sorry, I can't…' for broad queries.
    That's a no-results signal, not an error worth a 502 + frontend retry."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        "I am sorry, but I cannot fulfill this request. The query is too broad."
    )

    result = _make_provider().search(query="patagonia jacket")
    assert result.candidates == []


@patch("services.gemini.genai.Client")
def test_search_malformed_json_still_raises(mock_client_cls: MagicMock):
    """If the response looks like JSON ({...}) but doesn't parse, surface the
    error so retries/observability still kick in — that's a real provider bug."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response(
        '{"candidates": [{"url": broken json'
    )

    with pytest.raises(LlmInvalidResponseError, match="not valid JSON"):
        _make_provider().search(query="something")


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


@patch("services.gemini.time.sleep")
@patch("services.gemini.genai.Client")
def test_search_quota_error(mock_client_cls: MagicMock, mock_sleep: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.side_effect = genai_errors.APIError(
        429,
        {"error": {"status": "RESOURCE_EXHAUSTED", "message": "quota"}},
    )

    with pytest.raises(LlmQuotaExhaustedError):
        _make_provider().search(query="something")

    # Quota = hard daily cap; do not waste more requests.
    assert mock_client.models.generate_content.call_count == 1
    mock_sleep.assert_not_called()


@patch("services.gemini.time.sleep")
@patch("services.gemini.genai.Client")
def test_search_empty_response_raises_after_retries(
    mock_client_cls: MagicMock, mock_sleep: MagicMock
):
    """Empty grounded responses retry up to _GROUNDED_MAX_ATTEMPTS times before
    surfacing the empty-response error to the caller."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _mock_response("")

    with pytest.raises(LlmInvalidResponseError, match="empty search response"):
        _make_provider().search(query="something")

    # 3 grounded attempts total; sleeps between attempts only (2 sleeps).
    assert mock_client.models.generate_content.call_count == 3
    assert mock_sleep.call_count == 2


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
    from core.settings import DEFAULT_GEMINI_SEARCH_MODEL

    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    clear_settings_cache()
    provider = get_llm_provider(Settings(gemini_api_key="secret"))
    assert isinstance(provider, GeminiFlashLlmProvider)
    assert provider._search_timeout_s == DEFAULT_GEMINI_SEARCH_TIMEOUT_S
    # Search uses Flash-Lite by default (separate quota pool from Flash).
    assert provider._search_model == DEFAULT_GEMINI_SEARCH_MODEL


def test_get_llm_provider_with_key_honors_search_model_override(monkeypatch):
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    clear_settings_cache()
    provider = get_llm_provider(
        Settings(
            gemini_api_key="secret",
            gemini_model="gemini-2.5-flash",
            gemini_search_model="gemini-3-flash-preview",
        )
    )
    assert isinstance(provider, GeminiFlashLlmProvider)
    assert provider._model == "gemini-2.5-flash"
    assert provider._search_model == "gemini-3-flash-preview"


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
