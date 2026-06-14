"""Pytest hooks for integration test environment setup."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETUP_SCRIPT = ROOT / "scripts" / "setup_integration_env.py"


def pytest_configure(config) -> None:
    markexpr = config.getoption("markexpr") or ""
    if "integration" not in markexpr:
        return
    if not SETUP_SCRIPT.exists():
        return
    subprocess.run(
        [sys.executable, str(SETUP_SCRIPT)],
        cwd=ROOT,
        check=False,
    )
