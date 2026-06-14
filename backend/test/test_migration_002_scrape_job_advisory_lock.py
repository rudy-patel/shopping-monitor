"""Structural assertions over 002_scrape_job_advisory_lock.sql (no Supabase required)."""

from __future__ import annotations

from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "db"
    / "migrations"
    / "002_scrape_job_advisory_lock.sql"
)

ADVISORY_LOCK_KEY = 8675309


def _sql() -> str:
    assert MIGRATION_PATH.exists(), f"Missing migration: {MIGRATION_PATH}"
    return MIGRATION_PATH.read_text(encoding="utf-8")


def test_migration_file_exists():
    assert MIGRATION_PATH.is_file()


def test_try_acquire_scrape_all_lock_function():
    sql = _sql()
    assert "CREATE OR REPLACE FUNCTION public.try_acquire_scrape_all_lock()" in sql
    assert f"pg_try_advisory_lock({ADVISORY_LOCK_KEY})" in sql
    assert "SECURITY DEFINER" in sql
    assert "SET search_path = public" in sql


def test_release_scrape_all_lock_function():
    sql = _sql()
    assert "CREATE OR REPLACE FUNCTION public.release_scrape_all_lock()" in sql
    assert f"pg_advisory_unlock({ADVISORY_LOCK_KEY})" in sql
