"""Regression tests for integration env setup gating in conftest."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
_SUPABASE_ENV_KEYS = (
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_ACCESS_TOKEN",
    "SUPABASE_PAT",
    "SUPABASE_PROJECT_REF",
)


def test_unit_test_invocation_skips_integration_env_setup() -> None:
    """Regression: CI unit runs (-m 'not integration') must not invoke setup script."""
    env = os.environ.copy()
    for key in _SUPABASE_ENV_KEYS:
        env.pop(key, None)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "test/",
            "--collect-only",
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
    assert "Missing: SUPABASE" not in output
    assert "Wrote" not in output
    assert "Missing Supabase credentials for integration tests" not in output
