"""Manual live Gemini discovery smoke. NOT run in CI."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from core.settings import get_settings  # noqa: E402
from services.factory import get_llm_provider  # noqa: E402
from services.llm import NoOpLlmProvider  # noqa: E402


def main() -> int:
    if sys.version_info < (3, 12):
        print(
            "Python 3.12+ is required for the backend. "
            f"Current interpreter: {sys.version.split()[0]}",
            file=sys.stderr,
        )
        return 1

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call the real Gemini API (requires GEMINI_API_KEY). Never use in CI.",
    )
    args = parser.parse_args()

    if args.live:
        if not get_settings().gemini_api_key.strip():
            print("GEMINI_API_KEY is required for --live smoke.", file=sys.stderr)
            return 1
        llm = get_llm_provider()
        mode = "live"
    else:
        llm = NoOpLlmProvider()
        mode = "dry_run"

    started = time.perf_counter()
    result = llm.discover(
        title="Lenovo Yoga Slim 7x 14.5 Touchscreen Copilot+ PC Laptop",
        brand="Lenovo",
        retailer_slug="bestbuy_ca",
        variant_attributes={},
        image_url=None,
        reference_price_cents=179999,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    print(f"mode={mode}")
    print(f"candidate_count={len(result.candidates)}")
    print(f"elapsed_ms={elapsed_ms}")
    for index, candidate in enumerate(result.candidates, start=1):
        print(f"candidate_{index}={candidate.url}")
        print(f"justification_{index}={candidate.justification}")

    if args.live and result.candidates:
        print(json.dumps({"candidates": [c.model_dump(mode="json") for c in result.candidates]}))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
