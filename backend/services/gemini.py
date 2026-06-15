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

from core.logging import get_logger
from scrapers.exceptions import RetailerNotSupportedError
from scrapers.registry import all_retailers, lookup_by_url
from services.llm import (
    MAX_CLEAN_TITLE_LEN,
    MIN_CLEAN_TITLE_LEN,
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

logger = get_logger(__name__)

_VALID_CATEGORIES = frozenset({"clothing", "shoes", "home", "tech", "other"})
_MAX_DISCOVER_CANDIDATES = 8
_MAX_SEARCH_CANDIDATES = 8


class _GeminiCategoryPayload(BaseModel):
    category: str
    clean_title: str | None = None


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


def _validate_clean_title(value: str | None) -> str | None:
    """Drop oversized / undersized / whitespace-only LLM titles silently.

    Title cleanup is best-effort: a rejected title falls through to the scraped
    title in product_service. We never raise here — a bad title shouldn't fail
    categorization, since the category is the load-bearing field.
    """
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) < MIN_CLEAN_TITLE_LEN or len(cleaned) > MAX_CLEAN_TITLE_LEN:
        return None
    return cleaned


_GROUNDED_MAX_ATTEMPTS = 3
_GROUNDED_RETRY_BACKOFF_S = 1.0
# HTTP statuses Google returns when the grounded-search pipeline is briefly
# overloaded or a single attempt times out. Retrying is the documented mitigation
# (see python-genai#2249). 429 is intentionally NOT in this set — it's a daily
# free-tier quota cap and retrying just burns more quota for the same wall-time.
_TRANSIENT_RETRY_STATUS_CODES = frozenset({500, 502, 503, 504})


def _is_quota_error(exc: Exception) -> bool:
    if isinstance(exc, genai_errors.APIError):
        if exc.code == 429:
            return True
        if exc.status == "RESOURCE_EXHAUSTED":
            return True
    message = str(exc).lower()
    if "rate limit" in message or "too many requests" in message:
        return True
    return "quota" in message or "resource_exhausted" in message


def _is_transient_provider_error(exc: Exception) -> bool:
    """Brief Gemini-side hiccups (overload, deadline, server error) — safe to retry."""
    if isinstance(exc, genai_errors.APIError):
        if exc.code in _TRANSIENT_RETRY_STATUS_CODES:
            return True
        if exc.status in {"UNAVAILABLE", "DEADLINE_EXCEEDED", "INTERNAL"}:
            return True
    return False


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


def _extract_finish_reason(response: object) -> str | None:
    """Best-effort `finish_reason` string for diagnostic logging."""
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return None
    reason = getattr(candidates[0], "finish_reason", None)
    if reason is None:
        return None
    return getattr(reason, "name", str(reason))


def _summarize_exc(exc: Exception) -> str:
    """Short error string for log fields — full traceback stays in `logger.exception`."""
    code = getattr(exc, "code", None)
    status = getattr(exc, "status", None)
    if code or status:
        return f"{type(exc).__name__}({code or '-'} {status or '-'}): {str(exc)[:140]}"
    return f"{type(exc).__name__}: {str(exc)[:140]}"


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
        "Classify this Canadian retail product and produce a short, human-friendly "
        "name for the user's wishlist.\n"
        "Allowed category slugs (pick exactly one): clothing, shoes, home, tech, other\n"
        f"Scraped product title: {title}\n"
        f"Brand: {brand_text}\n"
        f"Retailer: {retailer_slug}\n"
        f"Breadcrumbs: {breadcrumb_text}\n"
        "\n"
        "Return JSON with two fields:\n"
        '- "category": one allowed slug above.\n'
        '- "clean_title": a concise display title for the same product. Keep brand + '
        "model/series + the variant attributes that distinguish it (color, capacity, size, "
        "edition). Strip retailer SEO suffixes, marketing adjectives, feature lists, "
        "shipping/membership perks, and trailing punctuation. Length 4-80 characters. "
        "Do not invent details, do not change the brand, and do not translate.\n"
        "\n"
        'Examples:\n'
        '- "Apple AirPods Pro 3 Noise Cancelling True Wireless Earbuds with MagSafe Charging Case" '
        '→ "Apple AirPods Pro 3"\n'
        '- "Lenovo Yoga Slim 7x 14.5\" Touchscreen Copilot+ PC Laptop - Cosmic Blue (Snapdragon X Elite/16GB/1TB SSD)" '
        '→ "Lenovo Yoga Slim 7x 14.5\\" - 16GB/1TB"\n'
        '- "Nintendo Switch OLED Model: Super Mario Bros. Wonder Bundle with 3-Month Online Individual Membership" '
        '→ "Nintendo Switch OLED - Mario Wonder Bundle"\n'
        "\n"
        'If the scraped title is already concise and clean, return it unchanged in '
        '"clean_title".'
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
    """Gemini Flash provider: structured categorization; prompt-parsed JSON for grounded search/discovery.

    Two models are wired:

    - ``model`` drives **categorization** (no grounding, structured JSON output,
      low-latency). Defaults align with the Flash family.
    - ``search_model`` drives **all grounded calls** — both ``search()`` and
      ``discover()`` — because they share the same google_search tool and free-tier
      RPD pool. Defaults to ``gemini-2.5-flash-lite``: the base ``gemini-2.5-flash``
      free-tier RPD for grounded queries is ~20/day (exhausts within minutes of
      normal use), while Flash-Lite has its own larger quota pool and returns
      grounded JSON in ~1-2s.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        search_model: str | None = None,
        default_timeout_s: float = 1.5,
        discover_timeout_s: float = 30.0,
        search_timeout_s: float = 20.0,
    ) -> None:
        if not api_key.strip():
            raise LlmQuotaExhaustedError("GEMINI_API_KEY not configured")
        self._model = model
        # Shared by search() and discover() — both grounded paths use the same model.
        self._search_model = search_model or model
        self._default_timeout_s = default_timeout_s
        self._discover_timeout_s = discover_timeout_s
        self._search_timeout_s = search_timeout_s
        self._client = genai.Client(api_key=api_key)

    def search(self, *, query: str, timeout_s: float | None = None) -> LlmSearchResult:
        prompt = _build_search_prompt(query)
        effective_timeout = (
            self._search_timeout_s if timeout_s is None else timeout_s
        )

        # `daemon` workers + a short shutdown so a stuck Gemini call doesn't
        # block the request thread (or our process) after we've already raised
        # LlmTimeoutError to the caller.
        pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gemini-search")
        try:
            future = pool.submit(
                self._call_gemini_grounded,
                prompt,
                model=self._search_model,
                empty_message="Gemini returned empty search response",
                call_label="search",
            )
            try:
                raw_text = future.result(timeout=effective_timeout)
            except FuturesTimeoutError as exc:
                logger.warning(
                    "gemini_search_timeout",
                    extra={
                        "model": self._search_model,
                        "timeout_s": effective_timeout,
                    },
                )
                raise LlmTimeoutError(
                    f"Gemini search timed out after {effective_timeout}s"
                ) from exc
            except (LlmInvalidResponseError, LlmQuotaExhaustedError, LlmProviderError):
                # _call_gemini_grounded already classified these; re-raising avoids
                # double-wrapping (e.g. LlmProviderError → LlmProviderError("...")).
                raise
            except Exception as exc:
                _raise_gemini_call_error(exc)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

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

        pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gemini-discover")
        try:
            future = pool.submit(
                self._call_gemini_grounded,
                prompt,
                model=self._search_model,
                empty_message="Gemini returned empty discovery response",
                call_label="discover",
            )
            try:
                raw_text = future.result(timeout=effective_timeout)
            except FuturesTimeoutError as exc:
                logger.warning(
                    "gemini_discover_timeout",
                    extra={
                        "model": self._search_model,
                        "timeout_s": effective_timeout,
                    },
                )
                raise LlmTimeoutError(
                    f"Gemini discover timed out after {effective_timeout}s"
                ) from exc
            except (LlmInvalidResponseError, LlmQuotaExhaustedError, LlmProviderError):
                raise
            except Exception as exc:
                _raise_gemini_call_error(exc)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

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

    def _call_gemini_grounded(
        self,
        prompt: str,
        *,
        model: str,
        empty_message: str,
        call_label: str,
    ) -> str:
        # Gemini 2.5 rejects controlled JSON schema alongside google_search grounding,
        # so we prompt for JSON and parse/validate locally. The grounded pipeline is
        # documented as flaky (python-genai#2249) — 503/504/500 are common transient
        # failures, while 429 is a daily-quota cap and is NOT retried.
        last_error: Exception | None = None
        for attempt in range(_GROUNDED_MAX_ATTEMPTS):
            attempt_started = time.perf_counter()
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                    ),
                )
                elapsed_ms = int((time.perf_counter() - attempt_started) * 1000)
                raw_text = _extract_grounded_response_text(response)
                finish_reason = _extract_finish_reason(response)
                if raw_text:
                    logger.info(
                        "gemini_grounded_success",
                        extra={
                            "call": call_label,
                            "model": model,
                            "attempt": attempt + 1,
                            "elapsed_ms": elapsed_ms,
                            "finish_reason": finish_reason,
                            "text_len": len(raw_text),
                        },
                    )
                    return raw_text
                # Empty grounded response — model decided not to use search results.
                # This is intermittent (model capacity rotation), so retry up to
                # _GROUNDED_MAX_ATTEMPTS - 1 times before surfacing the empty-response
                # error. We don't bucket this as a transient provider error because
                # the API call itself succeeded; only the payload was empty.
                logger.warning(
                    "gemini_grounded_empty_response",
                    extra={
                        "call": call_label,
                        "model": model,
                        "attempt": attempt + 1,
                        "elapsed_ms": elapsed_ms,
                        "finish_reason": finish_reason,
                    },
                )
                if attempt < _GROUNDED_MAX_ATTEMPTS - 1:
                    time.sleep(_GROUNDED_RETRY_BACKOFF_S * (attempt + 1))
                    continue
                raise LlmInvalidResponseError(empty_message)
            except LlmInvalidResponseError:
                raise
            except Exception as exc:
                elapsed_ms = int((time.perf_counter() - attempt_started) * 1000)
                last_error = exc
                if _is_quota_error(exc):
                    # Daily free-tier cap — retrying just burns more quota.
                    logger.warning(
                        "gemini_grounded_quota_exhausted",
                        extra={
                            "call": call_label,
                            "model": model,
                            "attempt": attempt + 1,
                            "elapsed_ms": elapsed_ms,
                            "error": _summarize_exc(exc),
                        },
                    )
                    _raise_gemini_call_error(exc)
                if (
                    _is_transient_provider_error(exc)
                    and attempt < _GROUNDED_MAX_ATTEMPTS - 1
                ):
                    logger.warning(
                        "gemini_grounded_transient_retry",
                        extra={
                            "call": call_label,
                            "model": model,
                            "attempt": attempt + 1,
                            "elapsed_ms": elapsed_ms,
                            "error": _summarize_exc(exc),
                        },
                    )
                    time.sleep(_GROUNDED_RETRY_BACKOFF_S * (attempt + 1))
                    continue
                logger.warning(
                    "gemini_grounded_failed",
                    extra={
                        "call": call_label,
                        "model": model,
                        "attempt": attempt + 1,
                        "elapsed_ms": elapsed_ms,
                        "error": _summarize_exc(exc),
                    },
                )
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
            clean_title=_validate_clean_title(payload.clean_title),
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
        cleaned = _extract_json_text(raw_text)
        # Gemini sometimes refuses with natural language ("I'm sorry, but…") on
        # broad/ambiguous queries. That isn't an error worth showing — it's just
        # "no good matches". Detect refusals (no leading `{`) and degrade
        # gracefully to empty results so the UI can offer "Add by URL" instead of
        # firing a 502 + frontend retry that would burn another grounded call.
        if not cleaned.lstrip().startswith("{"):
            logger.info(
                "gemini_search_non_json_response",
                extra={"text_preview": cleaned[:160]},
            )
            return LlmSearchResult(candidates=[])

        try:
            payload = _GeminiSearchPayload.model_validate_json(cleaned)
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
