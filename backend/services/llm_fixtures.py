"""Fixture-backed LLM provider for local dev / CI under SCRAPER_MODE=fixtures (T8.10).

Categorize: deterministic heuristic, never calls Gemini.
Discover: returns empty list by default (the existing search seed path covers cross-retailer
matching during dev); test code can subclass for richer fixtures.
Search: reads from ``backend/test/fixtures/search/<query_slug>.json``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from services.llm import (
    MAX_CLEAN_TITLE_LEN,
    MIN_CLEAN_TITLE_LEN,
    LlmCategorizationResult,
    LlmCategory,
    LlmDiscoveryResult,
    LlmInvalidResponseError,
    LlmSearchCandidate,
    LlmSearchResult,
)

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_DEFAULT_FIXTURE_DIR = _BACKEND_DIR / "test" / "fixtures" / "search"

_SLUG_NORMALIZE = re.compile(r"[^a-z0-9]+")
# First "stop" character that typically separates the core product name from
# retailer SEO suffixes / feature lists in scraped titles. We split here in
# fixtures-mode to mimic what the live LLM would return.
_FIXTURE_TITLE_SPLIT_RE = re.compile(r"\s*[,\-|:]\s")


def _shorten_title_for_fixtures(title: str) -> str | None:
    """Deterministic title shortener used by FixtureLlmProvider.

    Returns ``None`` when no meaningful shortening is possible so the caller
    falls through to the scraped title (matching live-LLM behavior on already-
    concise titles). Length bounds match the LLM contract (``MIN_CLEAN_TITLE_LEN``
    / ``MAX_CLEAN_TITLE_LEN``) so fixture-mode never produces a title that the
    real Gemini path would reject.
    """
    head = _FIXTURE_TITLE_SPLIT_RE.split(title.strip(), maxsplit=1)[0].strip()
    if not head or head == title.strip():
        return None
    if len(head) < MIN_CLEAN_TITLE_LEN or len(head) > MAX_CLEAN_TITLE_LEN:
        return None
    return head


def slugify_query(query: str) -> str:
    normalized = query.strip().lower()
    return _SLUG_NORMALIZE.sub("-", normalized).strip("-")


def _load_fixture(fixture_dir: Path, slug: str) -> dict | None:
    candidate = fixture_dir / f"{slug}.json"
    if not candidate.is_file():
        return None
    try:
        return json.loads(candidate.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LlmInvalidResponseError(
            f"Search fixture {candidate} is not valid JSON"
        ) from exc


class FixtureLlmProvider:
    """Local-dev LLM that reads canned search results from disk."""

    def __init__(self, fixture_dir: Path | None = None) -> None:
        self._fixture_dir = fixture_dir or _DEFAULT_FIXTURE_DIR

    def discover(
        self,
        *,
        title: str,
        brand: str | None,
        retailer_slug: str,
        variant_attributes: Mapping[str, str],
        image_url: str | None,
        reference_price_cents: int | None = None,
    ) -> LlmDiscoveryResult:
        # Cross-retailer discovery is exercised through the search-seed path in fixture mode.
        return LlmDiscoveryResult(candidates=[])

    def categorize(
        self,
        *,
        title: str,
        brand: str | None,
        retailer_slug: str,
        breadcrumbs: Sequence[str],
        timeout_s: float = 1.5,
    ) -> LlmCategorizationResult:
        # Deterministic guess so local dev sees a non-`other` chip when obvious.
        lowered = (title + " " + (brand or "")).lower()
        category: LlmCategory = "other"
        if any(word in lowered for word in ("laptop", "iphone", "ipad", "headphone", "tv")):
            category = "tech"
        elif any(word in lowered for word in ("shirt", "hoodie", "jacket", "tee", "pants")):
            category = "clothing"
        elif any(word in lowered for word in ("shoe", "sneaker", "boot", "sandal")):
            category = "shoes"
        elif any(word in lowered for word in ("lamp", "rug", "sofa", "pillow", "kitchen")):
            category = "home"
        return LlmCategorizationResult(
            category=category,
            clean_title=_shorten_title_for_fixtures(title),
        )

    def search(self, *, query: str, timeout_s: float = 5.0) -> LlmSearchResult:
        slug = slugify_query(query)
        if not slug:
            return LlmSearchResult(candidates=[])
        raw = _load_fixture(self._fixture_dir, slug)
        if raw is None:
            # Unknown query in fixture mode → empty results (UI surfaces empty state).
            return LlmSearchResult(candidates=[])
        candidates_raw = raw.get("candidates") or []
        candidates: list[LlmSearchCandidate] = []
        for item in candidates_raw:
            try:
                candidates.append(LlmSearchCandidate.model_validate(item))
            except Exception:
                continue
        return LlmSearchResult(candidates=cast(list, candidates))
