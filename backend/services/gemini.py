"""Gemini Flash LLM provider for categorization, discovery, and search (PRD §7.7, §10.7)."""

from __future__ import annotations

import re
import time
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
    LlmSearchCandidate,
    LlmSearchResult,
    LlmTimeoutError,
)

_VALID_CATEGORIES = frozenset({"clothing", "shoes", "home", "tech", "other"})
_MAX_DISCOVER_CANDIDATES = 8
_MAX_SEARCH_CANDIDATES = 8


class _GeminiCategoryPayload(BaseModel):
    category: str


class _GeminiDiscoverCandidatePayload(BaseModel):
    url: str
    justification: str = Field(max_length=280)


class _GeminiDiscoverPayload(BaseModel):
    candidates: list[_GeminiDiscoverCandidatePayload] = Field(default_factory=list)


class _GeminiSearchCandidatePayload(BaseModel):
    url: str
    title: str = Field(min_length=1, max_length=280)
    retailer_hint: str | None = Field(default=None, max_length=120)
    brand_hint: str | None = Field(default=None, max_length=120)
    justification: str = Field(max_length=200)


class _GeminiSearchPayload(BaseModel):
    candidates: list[_GeminiSearchCandidatePayload] = Field(default_factory=list)


_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _extract_json_text(raw_text: str) -> str:
    """Strip optional markdown fences before parsing grounded-search JSON."""
    stripped = raw_text.strip()
    if stripped.startswith("```"):
        stripped = _JSON_FENCE_RE.sub("", stripped).strip()
    return stripped


_GROUNDED_MAX_ATTEMPTS = 3
_GROUNDED_RETRY_BACKOFF_S = 2.0


def _is_rate_limit_error(exc: Exception) -> bool:
    if isinstance(exc, genai_errors.APIError) and exc.code == 429:
        return True
    message = str(exc).lower()
    return "rate limit" in message or "too many requests" in message


def _extract_grounded_response_text(response: object) -> str | None:
    """Best-effort text from a grounded response; SDK `text` can be None."""
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return None
    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None) or []
    chunks: list[str] = []
    for part in parts:
        part_text = getattr(part, "text", None)
        if isinstance(part_text, str) and part_text:
            chunks.append(part_text)
    joined = "".join(chunks).strip()
    return joined or None


def _is_quota_error(exc: Exception) -> bool:
    if _is_rate_limit_error(exc):
        return True
    if isinstance(exc, genai_errors.APIError):
        if exc.status == "RESOURCE_EXHAUSTED":
            return True
    message = str(exc).lower()
    return "quota" in message or "resource_exhausted" in message


def _raise_gemini_call_error(exc: Exception) -> None:
    if _is_quota_error(exc):
        raise LlmQuotaExhaustedError(str(exc)) from exc
    raise LlmProviderError(str(exc)) from exc


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


def _build_search_prompt(query: str) -> str:
    """Free-text user query → ranked Canadian product page candidates."""
    retailers = "\n".join(_supported_retailer_lines())
    return (
        "Find Canadian product pages for the user's search query.\n"
        "Constraints:\n"
        "- Return product detail page URLs only (PDPs), not category/search pages.\n"
        "- Canadian listings only: prefer .ca domains or each retailer's Canadian storefront.\n"
        "- Do NOT include US-only listings, marketplace third-party sellers, eBay, or AliExpress.\n"
        "- Prefer the supported retailers below when they carry the product; you may also include\n"
        "  other reputable Canadian retailers (e.g. walmart.ca, well.ca, londondrugs.com, mec.ca,\n"
        "  staples.ca, structube.com, hbc.com, etc.) when supported retailers don't carry it.\n"
        "- Each retailer should appear at most once. Pick the most canonical PDP per retailer.\n"
        "- Order results by how confident you are it matches the user's query.\n"
        "- Up to 8 candidates. Fewer is better than padding with low-confidence guesses.\n"
        "Supported retailers (prefer these):\n"
        f"{retailers}\n"
        f"User query: {query}\n"
        "Return ONLY valid JSON (no markdown fences or commentary) with this shape:\n"
        '{"candidates":[{"url":"https://...","title":"...","retailer_hint":"...","brand_hint":"...","justification":"..."}]}\n'
        "Field notes:\n"
        '- title: the actual product name (not the page title with site suffix)\n'
        '- retailer_hint: human label e.g. "Best Buy Canada", "Walmart Canada"\n'
        '- brand_hint: best-effort brand name if you can identify it, else null\n'
        '- justification: one short line explaining why this matches the query (max 200 chars)'
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
        "Return ONLY valid JSON (no markdown fences or commentary) with up to 8 candidates "
        "ordered by confidence:\n"
        '{"candidates":[{"url":"https://...","justification":"one line why it matches"}]}'
    )


class GeminiFlashLlmProvider:
    """Gemini Flash provider: structured categorization; prompt-parsed JSON for grounded search/discovery."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        default_timeout_s: float = 1.5,
        discover_timeout_s: float = 30.0,
        search_timeout_s: float = 5.0,
    ) -> None:
        if not api_key.strip():
            raise LlmQuotaExhaustedError("GEMINI_API_KEY not configured")
        self._model = model
        self._default_timeout_s = default_timeout_s
        self._discover_timeout_s = discover_timeout_s
        self._search_timeout_s = search_timeout_s
        self._client = genai.Client(api_key=api_key)

    def search(self, *, query: str, timeout_s: float | None = None) -> LlmSearchResult:
        prompt = _build_search_prompt(query)
        effective_timeout = (
            self._search_timeout_s if timeout_s is None else timeout_s
        )

        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    self._call_gemini_grounded,
                    prompt,
                    empty_message="Gemini returned empty search response",
                )
                try:
                    raw_text = future.result(timeout=effective_timeout)
                except FuturesTimeoutError as exc:
                    raise LlmTimeoutError(
                        f"Gemini search timed out after {effective_timeout}s"
                    ) from exc
        except (LlmTimeoutError, LlmInvalidResponseError, LlmQuotaExhaustedError):
            raise
        except Exception as exc:
            _raise_gemini_call_error(exc)

        return self._parse_search_response(raw_text)

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
                future = pool.submit(
                    self._call_gemini_grounded,
                    prompt,
                    empty_message="Gemini returned empty discovery response",
                )
                try:
                    raw_text = future.result(timeout=effective_timeout)
                except FuturesTimeoutError as exc:
                    raise LlmTimeoutError(
                        f"Gemini discover timed out after {effective_timeout}s"
                    ) from exc
        except (LlmTimeoutError, LlmInvalidResponseError, LlmQuotaExhaustedError):
            raise
        except Exception as exc:
            _raise_gemini_call_error(exc)

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
            _raise_gemini_call_error(exc)

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

    def _call_gemini_grounded(self, prompt: str, *, empty_message: str) -> str:
        # Gemini 2.5 rejects controlled JSON schema alongside google_search grounding.
        # Prompt for JSON and parse/validate locally instead.
        last_error: Exception | None = None
        for attempt in range(_GROUNDED_MAX_ATTEMPTS):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                    ),
                )
                raw_text = _extract_grounded_response_text(response)
                if raw_text:
                    return raw_text
                raise LlmInvalidResponseError(empty_message)
            except LlmInvalidResponseError:
                raise
            except Exception as exc:
                last_error = exc
                if _is_rate_limit_error(exc) and attempt < _GROUNDED_MAX_ATTEMPTS - 1:
                    time.sleep(_GROUNDED_RETRY_BACKOFF_S * (attempt + 1))
                    continue
                _raise_gemini_call_error(exc)
        if last_error is not None:
            _raise_gemini_call_error(last_error)
        raise LlmInvalidResponseError(empty_message)

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
            payload = _GeminiDiscoverPayload.model_validate_json(_extract_json_text(raw_text))
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

    def _parse_search_response(self, raw_text: str) -> LlmSearchResult:
        try:
            payload = _GeminiSearchPayload.model_validate_json(_extract_json_text(raw_text))
        except Exception as exc:
            raise LlmInvalidResponseError(
                f"Gemini search response was not valid JSON: {raw_text!r}"
            ) from exc

        if len(payload.candidates) > _MAX_SEARCH_CANDIDATES:
            raise LlmInvalidResponseError(
                f"Gemini returned more than {_MAX_SEARCH_CANDIDATES} search candidates"
            )

        candidates: list[LlmSearchCandidate] = []
        for item in payload.candidates:
            try:
                candidates.append(
                    LlmSearchCandidate(
                        url=item.url,
                        title=item.title.strip(),
                        retailer_hint=(item.retailer_hint or None),
                        brand_hint=(item.brand_hint or None),
                        justification=item.justification,
                    )
                )
            except Exception:
                continue

        return LlmSearchResult(candidates=candidates)
