"""Cross-retailer listing match confidence scoring (PRD §7.3, T3.1)."""

from __future__ import annotations

import re
from typing import Literal

AUTO_ADD_THRESHOLD = 0.85
NEEDS_REVIEW_MIN = 0.60

WEIGHT_TITLE_JACCARD = 0.444
WEIGHT_BRAND_EXACT = 0.222
WEIGHT_VARIANT_EXACT = 0.333

MatchClassification = Literal["auto_add", "needs_review", "discard"]

_PUNCTUATION_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def tokenize_title(title: str) -> set[str]:
    normalized = _PUNCTUATION_RE.sub(" ", title.lower())
    return {token for token in normalized.split() if token}


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    union = len(left | right)
    return intersection / union if union else 0.0


def _normalize_brand(brand: str | None) -> str | None:
    if brand is None:
        return None
    stripped = brand.strip()
    return stripped.lower() if stripped else None


def _normalize_variant_dict(attrs: dict[str, str]) -> dict[str, str]:
    return {key.lower().strip(): value.strip().lower() for key, value in attrs.items()}


def variant_exact_match_score(
    reference: dict[str, str],
    candidate: dict[str, str],
) -> float:
    if not reference:
        return 1.0
    ref_norm = _normalize_variant_dict(reference)
    cand_norm = _normalize_variant_dict(candidate)
    return 1.0 if ref_norm == cand_norm else 0.0


def brand_exact_match_score(
    reference_brand: str | None,
    candidate_brand: str | None,
) -> float:
    ref = _normalize_brand(reference_brand)
    if ref is None:
        return 0.0
    cand = _normalize_brand(candidate_brand)
    if cand is None:
        return 0.0
    return 1.0 if ref == cand else 0.0


def compute_match_confidence(
    *,
    reference_title: str,
    reference_brand: str | None,
    reference_variants: dict[str, str],
    candidate_title: str,
    candidate_brand: str | None,
    candidate_variants: dict[str, str],
) -> float:
    title_score = jaccard_similarity(
        tokenize_title(reference_title),
        tokenize_title(candidate_title),
    )
    brand_score = brand_exact_match_score(reference_brand, candidate_brand)
    variant_score = variant_exact_match_score(reference_variants, candidate_variants)

    total = (
        WEIGHT_TITLE_JACCARD * title_score
        + WEIGHT_BRAND_EXACT * brand_score
        + WEIGHT_VARIANT_EXACT * variant_score
    )
    return round(total, 3)


def classify_match(score: float) -> MatchClassification:
    if score >= AUTO_ADD_THRESHOLD:
        return "auto_add"
    if score >= NEEDS_REVIEW_MIN:
        return "needs_review"
    return "discard"
