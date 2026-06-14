"""Gemini Flash LLM provider for categorization (PRD §7.7, T2.4)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import cast

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from services.llm import (
    LlmCategory,
    LlmCategorizationResult,
    LlmDiscoveryResult,
    LlmInvalidResponseError,
    LlmProviderError,
    LlmQuotaExhaustedError,
    LlmTimeoutError,
)

_VALID_CATEGORIES = frozenset({"clothing", "shoes", "home", "tech", "other"})


class _GeminiCategoryPayload(BaseModel):
    category: str


def _is_quota_error(exc: Exception) -> bool:
    if isinstance(exc, genai_errors.APIError):
        if exc.code == 429:
            return True
        if exc.status == "RESOURCE_EXHAUSTED":
            return True
    message = str(exc).lower()
    return "quota" in message or "resource_exhausted" in message


def _build_categorize_prompt(
    *,
    title: str,
    brand: str | None,
    retailer_slug: str,
    breadcrumbs: Sequence[str],
) -> str:
    breadcrumb_text = ", ".join(breadcrumbs) if breadcrumbs else "none"
    brand_text = brand or "unknown"
    return (
        "Classify this Canadian retail product into exactly one category slug.\n"
        "Allowed slugs (pick exactly one): clothing, shoes, home, tech, other\n"
        f"Product title: {title}\n"
        f"Brand: {brand_text}\n"
        f"Retailer: {retailer_slug}\n"
        f"Breadcrumbs: {breadcrumb_text}\n"
        'Return JSON with a single "category" field containing one allowed slug.'
    )


class GeminiFlashLlmProvider:
    """Gemini Flash structured-output categorization; discover stubbed for T3.1."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        default_timeout_s: float = 1.5,
    ) -> None:
        if not api_key.strip():
            raise LlmQuotaExhaustedError("GEMINI_API_KEY not configured")
        self._model = model
        self._default_timeout_s = default_timeout_s
        self._client = genai.Client(api_key=api_key)

    def discover(
        self,
        *,
        title: str,
        brand: str | None,
        retailer_slug: str,
        variant_attributes: Mapping[str, str],
        image_url: str | None,
    ) -> LlmDiscoveryResult:
        return LlmDiscoveryResult(candidates=[])

    def categorize(
        self,
        *,
        title: str,
        brand: str | None,
        retailer_slug: str,
        breadcrumbs: Sequence[str],
        timeout_s: float | None = None,
    ) -> LlmCategorizationResult:
        prompt = _build_categorize_prompt(
            title=title,
            brand=brand,
            retailer_slug=retailer_slug,
            breadcrumbs=breadcrumbs,
        )
        effective_timeout = (
            self._default_timeout_s if timeout_s is None else timeout_s
        )

        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self._call_gemini, prompt)
                try:
                    raw_text = future.result(timeout=effective_timeout)
                except FuturesTimeoutError as exc:
                    raise LlmTimeoutError(
                        f"Gemini categorize timed out after {effective_timeout}s"
                    ) from exc
        except (LlmTimeoutError, LlmInvalidResponseError, LlmQuotaExhaustedError):
            raise
        except Exception as exc:
            if _is_quota_error(exc):
                raise LlmQuotaExhaustedError(str(exc)) from exc
            raise LlmProviderError(str(exc)) from exc

        return self._parse_categorize_response(raw_text)

    def _call_gemini(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_GeminiCategoryPayload,
            ),
        )
        raw_text = response.text
        if not raw_text:
            raise LlmInvalidResponseError("Gemini returned empty categorization response")
        return raw_text

    def _parse_categorize_response(self, raw_text: str) -> LlmCategorizationResult:
        try:
            payload = _GeminiCategoryPayload.model_validate_json(raw_text)
        except Exception as exc:
            raise LlmInvalidResponseError(
                f"Gemini categorization response was not valid JSON: {raw_text!r}"
            ) from exc

        if payload.category not in _VALID_CATEGORIES:
            raise LlmInvalidResponseError(
                f"Gemini returned invalid category slug: {payload.category!r}"
            )

        return LlmCategorizationResult(
            category=cast(LlmCategory, payload.category),
            raw_response=raw_text,
        )
