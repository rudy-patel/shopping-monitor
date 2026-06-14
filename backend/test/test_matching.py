"""Match confidence scoring tests."""

from __future__ import annotations

import pytest

from services.matching import (
    AUTO_ADD_THRESHOLD,
    NEEDS_REVIEW_MIN,
    classify_match,
    compute_match_confidence,
    jaccard_similarity,
    tokenize_title,
    variant_exact_match_score,
)


def test_perfect_match_scores_one():
    title = "Sony WH-1000XM5 Wireless Headphones"
    score = compute_match_confidence(
        reference_title=title,
        reference_brand="Sony",
        reference_variants={"color": "Black"},
        candidate_title=title,
        candidate_brand="Sony",
        candidate_variants={"color": "Black"},
    )
    assert score >= AUTO_ADD_THRESHOLD
    assert classify_match(score) == "auto_add"


def test_empty_reference_variants_score_full_variant_term():
    assert variant_exact_match_score({}, {"color": "Black"}) == 1.0
    score = compute_match_confidence(
        reference_title="USB-C Hub",
        reference_brand=None,
        reference_variants={},
        candidate_title="USB-C Hub",
        candidate_brand=None,
        candidate_variants={"color": "Black"},
    )
    assert score == round(0.444 + 0.333, 3)


def test_missing_reference_brand_zeros_brand_term():
    score = compute_match_confidence(
        reference_title="USB-C Hub",
        reference_brand=None,
        reference_variants={},
        candidate_title="USB-C Hub",
        candidate_brand="Anker",
        candidate_variants={},
    )
    assert score == round(0.444 + 0.333, 3)


def test_boundary_needs_review_at_0600():
    score = 0.600
    assert classify_match(score) == "needs_review"


def test_boundary_discard_below_0600():
    assert classify_match(0.599) == "discard"


def test_boundary_auto_add_at_0850():
    assert classify_match(0.850) == "auto_add"


def test_boundary_needs_review_at_0849():
    assert classify_match(0.849) == "needs_review"


def test_jaccard_empty_titles():
    assert jaccard_similarity(set(), set()) == 1.0


def test_tokenize_strips_punctuation():
    tokens = tokenize_title("Hello, World!")
    assert tokens == {"hello", "world"}


def test_variant_mismatch_zeros_variant_term():
    score = compute_match_confidence(
        reference_title="Shirt",
        reference_brand="Brand",
        reference_variants={"size": "M"},
        candidate_title="Shirt",
        candidate_brand="Brand",
        candidate_variants={"size": "L"},
    )
    assert score == round(0.444 + 0.222, 3)


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ({"a"}, {"a"}, 1.0),
        ({"a"}, {"b"}, 0.0),
        (set(), {"a"}, 0.0),
    ],
)
def test_jaccard_edge_cases(left, right, expected):
    assert jaccard_similarity(left, right) == expected


def test_needs_review_min_constant():
    assert NEEDS_REVIEW_MIN == 0.60
