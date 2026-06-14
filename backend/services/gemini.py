"""Gemini Flash LLM provider for categorization and discovery (PRD §7.7, §10.7)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import cast

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, Field

from scrapers.exceptions import RetailerNotSupportedError
from scrapers.registry import all_retailers, lookup_by_url
from services.llm import (
    LlmCategory,
    LlmCategorizationResult,
    LlmDiscoveryCandidate,
    LlmDiscoveryResult,
    LlmInvalidResponseError,
    LlmProviderError,
    LlmQuotaExhaustedError,
    LlmTimeoutError,
)

_VALID_CATEGORIES = frozenset({"clothing", "shoes", "home", "tech", "other"})
_MAX_DISCOVER_CANDIDATES = 8


class _GeminiCategoryPayload(BaseModel):
    category: str


class _GeminiDiscoverCandidatePayload(BaseModel):
    url: str
    justification: str = Field(max_length=280)


class _GeminiDiscoverPayload(BaseModel):
    candidates: list[_GeminiDiscoverCandidatePayload] = Field(default_factory=list)


def _is_quota_error(exc: Exception) -> bool:
    if isinstance(exc, genai_errors.APIError):
        if exc.code == 429:
            return True
        if exc.status == "RESOURCE_EXHAUSTED":
            return True
    message = str(exc).lower()
    return "quota" in message or "resource_exhausted" in message


def _supported_retailer_lines() -> list[str]:
    lines: list[str] = []
    for entry in all_retailers():
        if entry.slug == "generic":
            continue
        domains = ", ".join(entry.domains) if entry.domains else "unknown"
        lines.append(f"- {entry.slug}: {domains}")
    return lines


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


def _build_discover_prompt(
    *,
    title: str,
    brand: str | None,
    retailer_slug: str,
    variant_attributes: Mapping[str, str],
    image_url: str | None,
    reference_price_cents: int | None,
) -> str:
    brand_text = brand or "unknown"
    variant_json = dict(variant_attributes)
    retailers = "\n".join(_supported_retailer_lines())
    image_line = image_url or "none"
    if reference_price_cents is not None:
        price_line = f"{reference_price_cents} CAD cents"
    else:
        price_line = "unknown"
    return (
        "Find Canadian retailer product pages for the exact same product variant.\n"
        "Search only supported retailers (exclude generic/unlisted domains).\n"
        "Prefer .ca domains or each retailer's Canadian storefront.\n"
        f"Reference title: {title}\n"
        f"Reference brand: {brand_text}\n"
        f"Primary retailer: {retailer_slug}\n"
        f"Variant attributes (JSON): {variant_json}\n"
        f"Reference price: {price_line}\n"
        f"Reference image URL: {image_line}\n"
        "Supported retailers:\n"
        f"{retailers}\n"
        "Return JSON with up to 8 candidates ordered by confidence.\n"
        'Each candidate: {"url": "https://...", "justification": "one line why it matches"}'
    )


class GeminiFlashLlmProvider:
    """Gemini Flash structured-output categorization and discovery."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        default_timeout_s: float = 1.5,
        discover_timeout_s: float = 30.0,
    ) -> None:
        if not api_key.strip():
            raise LlmQuotaExhaustedError("GEMINI_API_KEY not configured")
        self._model = model
        self._default_timeout_s = default_timeout_s
        self._discover_timeout_s = discover_timeout_s
        self._client = genai.Client(api_key=api_key)

    def discover(
        self,
        *,
        title: str,
        brand: str | None,
        retailer_slug: str,
        variant_attributes: Mapping[str, str],
        image_url: str | None,
        reference_price_cents: int | None = None,
        timeout_s: float | None = None,
    ) -> LlmDiscoveryResult:
        prompt = _build_discover_prompt(
            title=title,
            brand=brand,
            retailer_slug=retailer_slug,
            variant_attributes=variant_attributes,
            image_url=image_url,
            reference_price_cents=reference_price_cents,
        )
        effective_timeout = (
            self._discover_timeout_s if timeout_s is None else timeout_s
        )

        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self._call_gemini_discover, prompt)
                try:
                    raw_text = future.result(timeout=effective_timeout)
                except FuturesTimeoutError as exc:
                    raise LlmTimeoutError(
                        f"Gemini discover timed out after {effective_timeout}s"
                    ) from exc
        except (LlmTimeoutError, LlmInvalidResponseError, LlmQuotaExhaustedError):
            raise
        except Exception as exc:
            if _is_quota_error(exc):
                raise LlmQuotaExhaustedError(str(exc)) from exc
            raise LlmProviderError(str(exc)) from exc

        return self._parse_discover_response(raw_text)

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
                future = pool.submit(self._call_gemini_categorize, prompt)
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

    def _call_gemini_categorize(self, prompt: str) -> str:
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

    def _call_gemini_discover(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_GeminiDiscoverPayload,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        raw_text = response.text
        if not raw_text:
            raise LlmInvalidResponseError("Gemini returned empty discovery response")
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

    def _parse_discover_response(self, raw_text: str) -> LlmDiscoveryResult:
        try:
            payload = _GeminiDiscoverPayload.model_validate_json(raw_text)
        except Exception as exc:
            raise LlmInvalidResponseError(
                f"Gemini discovery response was not valid JSON: {raw_text!r}"
            ) from exc

        if len(payload.candidates) > _MAX_DISCOVER_CANDIDATES:
            raise LlmInvalidResponseError(
                f"Gemini returned more than {_MAX_DISCOVER_CANDIDATES} candidates"
            )

        filtered: list[LlmDiscoveryCandidate] = []
        for item in payload.candidates:
            try:
                entry = lookup_by_url(item.url)
            except RetailerNotSupportedError:
                continue
            if entry.slug == "generic":
                continue
            filtered.append(
                LlmDiscoveryCandidate(url=item.url, justification=item.justification)
            )

        return LlmDiscoveryResult(candidates=filtered)
