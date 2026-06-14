"""Regression tests ensuring pytest never calls live Gemini."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_unit_tests_pass_with_gemini_key_in_env_without_live_calls() -> None:
    """Regression: a GEMINI_API_KEY in the shell must not enable live API calls in pytest."""
    env = os.environ.copy()
    env["GEMINI_API_KEY"] = "ci-should-not-call-this"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "test/test_services_gemini.py",
            "-q",
            "-m",
            "not integration",
        ],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
