"""Field evaluation and blocked-response detection."""

from __future__ import annotations

import re

from scrapers.benchmark.types import FieldExpect, FieldResult, StrategyFields
from scrapers.extraction.types import ExtractedFields

_BLOCKED_STATUS_CODES = frozenset({403, 429, 503})
_BLOCKED_BODY_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cloudflare", re.compile(r"cloudflare", re.I)),
    ("access_denied", re.compile(r"access denied", re.I)),
    ("cf_browser_verification", re.compile(r"cf-browser-verification", re.I)),
    ("captcha", re.compile(r"captcha", re.I)),
    ("challenge_platform", re.compile(r"challenge-platform", re.I)),
    ("attention_required", re.compile(r"attention required", re.I)),
)


def detect_blocked_markers(status_code: int, body_text: str) -> list[str]:
    markers: list[str] = []
    if status_code in _BLOCKED_STATUS_CODES:
        markers.append(str(status_code))
    for name, pattern in _BLOCKED_BODY_MARKERS:
        if pattern.search(body_text):
            markers.append(name)
    return markers


def skipped_fields(reason: str) -> StrategyFields:
    """Neutral field rows for strategies that were not executed."""
    skipped = FieldResult(ok=True, reason=reason)
    return StrategyFields(
        title=skipped,
        price=skipped,
        stock=skipped,
        image=skipped,
        variants=skipped,
    )


def evaluate_fields(
    extracted: ExtractedFields | None,
    *,
    expect: FieldExpect,
    error: str | None = None,
) -> StrategyFields:
    if extracted is None:
        missing_reason = error or "extraction_failed"
        return StrategyFields(
            title=_field_result(False, expect.title, reason=missing_reason),
            price=_field_result(False, expect.price, reason=missing_reason),
            stock=_field_result(False, expect.stock, reason=missing_reason),
            image=_field_result(False, expect.image, reason=missing_reason),
            variants=_field_result(False, expect.variants, reason=missing_reason),
        )

    return StrategyFields(
        title=_field_result(bool(extracted.title), expect.title, value=extracted.title),
        price=_field_result(
            extracted.price_cents is not None,
            expect.price,
            value=extracted.price_cents,
        ),
        stock=_field_result(
            extracted.is_in_stock is not None,
            expect.stock,
            value=extracted.is_in_stock,
        ),
        image=_field_result(
            bool(extracted.image_url),
            expect.image,
            value=extracted.image_url,
        ),
        variants=_field_result(
            len(extracted.available_variants) > 0,
            expect.variants,
            value=len(extracted.available_variants),
        ),
    )


def _field_result(
    present: bool,
    expected: bool,
    *,
    value: object | None = None,
    reason: str | None = None,
) -> FieldResult:
    if not expected:
        return FieldResult(ok=True, value=value, reason="not_required")
    if present:
        return FieldResult(ok=True, value=value)
    return FieldResult(ok=False, reason=reason or "missing")


def score_strategy_fields(fields: StrategyFields, expect: FieldExpect) -> int:
    score = 0
    if expect.title and fields.title.ok:
        score += 1
    if expect.price and fields.price.ok:
        score += 1
    if expect.stock and fields.stock.ok:
        score += 1
    if expect.image and fields.image.ok:
        score += 1
    if expect.variants and fields.variants.ok:
        score += 1
    return score


def has_title_or_price(fields: StrategyFields) -> bool:
    return fields.title.ok or fields.price.ok
