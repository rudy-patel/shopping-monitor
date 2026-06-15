"""Structural assertions over 003_search_cache.sql (Pattern B, no Supabase required)."""

from __future__ import annotations

from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "db"
    / "migrations"
    / "003_search_cache.sql"
)


def _sql() -> str:
    assert MIGRATION_PATH.exists(), f"Missing migration: {MIGRATION_PATH}"
    return MIGRATION_PATH.read_text(encoding="utf-8")


def test_migration_file_exists():
    assert MIGRATION_PATH.is_file()


def test_creates_search_cache_table():
    sql = _sql()
    assert "CREATE TABLE public.search_cache" in sql


def test_rls_enabled():
    sql = _sql()
    assert "ALTER TABLE public.search_cache ENABLE ROW LEVEL SECURITY" in sql


def test_no_authenticated_policies_pattern_b():
    sql = _sql()
    # Pattern B: backend-only — no policies for the authenticated role.
    assert "TO authenticated" not in sql
    assert "FOR SELECT" not in sql
    assert "CREATE POLICY" not in sql


def test_index_on_fetched_at():
    sql = _sql()
    assert "CREATE INDEX search_cache_fetched_at_idx" in sql


def test_query_hash_is_primary_key():
    sql = _sql()
    assert "query_hash text PRIMARY KEY" in sql
