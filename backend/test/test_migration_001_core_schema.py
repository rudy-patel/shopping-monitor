"""Structural assertions over 001_core_schema.sql (no Supabase required)."""

from __future__ import annotations

import re
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "db" / "migrations" / "001_core_schema.sql"
)

TABLES = [
    "profiles",
    "products",
    "product_listings",
    "price_history",
    "notifications",
    "fx_rates_cache",
]

PATTERN_A_TABLES = [
    "profiles",
    "products",
    "product_listings",
    "price_history",
    "notifications",
]

POLICY_OPS = ("FOR SELECT", "FOR INSERT", "FOR UPDATE", "FOR DELETE")

ENUM_STRINGS = [
    "CAD", "USD", "EUR", "GBP",
    "light", "dark",
    "clothing", "shoes", "home", "tech", "other",
    "active", "needs_input", "archived",
    "pending", "running", "complete", "failed",
    "manual", "llm", "heuristic", "default_other",
    "auto_added", "needs_review", "accepted", "rejected",
    "ok", "failing", "blocked",
    "price_drop", "back_in_stock", "discovery_complete",
    "scrape_failing", "revisit_on_sale", "revisit_stale",
    "scheduled",
]

INDEXES = [
    "products_user_status_idx",
    "products_user_id_idx",
    "product_listings_product_id_idx",
    "price_history_listing_id_idx",
    "price_history_observed_at_idx",
    "notifications_user_created_idx",
    "notifications_created_at_idx",
]

UPDATED_AT_TABLES = ("profiles", "products", "product_listings")


def _sql() -> str:
    assert MIGRATION_PATH.exists(), f"Missing migration: {MIGRATION_PATH}"
    return MIGRATION_PATH.read_text(encoding="utf-8")


def test_migration_file_exists():
    assert MIGRATION_PATH.is_file()


def test_all_tables_created():
    sql = _sql()
    for table in TABLES:
        assert f"CREATE TABLE public.{table}" in sql


def test_rls_enabled_on_all_tables():
    sql = _sql()
    for table in TABLES:
        assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY" in sql


def test_pattern_a_has_four_policies_each():
    sql = _sql()
    for table in PATTERN_A_TABLES:
        for op in POLICY_OPS:
            pattern = rf"CREATE POLICY \w+ ON public\.{table} {re.escape(op)}"
            assert re.search(pattern, sql), f"Missing {op} policy on {table}"


def test_fx_rates_cache_has_no_policies():
    sql = _sql()
    policy_blocks = sql.split("CREATE POLICY")
    for block in policy_blocks[1:]:
        assert "ON public.fx_rates_cache" not in block


def test_enum_check_constraint_strings():
    sql = _sql()
    for value in ENUM_STRINGS:
        assert f"'{value}'" in sql, f"Missing enum/check value: {value}"


def test_cascade_foreign_keys():
    sql = _sql()
    assert "REFERENCES auth.users(id) ON DELETE CASCADE" in sql
    assert "REFERENCES public.products(id) ON DELETE CASCADE" in sql
    assert "REFERENCES public.product_listings(id) ON DELETE CASCADE" in sql
    assert sql.count("ON DELETE CASCADE") >= 6


def test_required_indexes():
    sql = _sql()
    for index_name in INDEXES:
        assert index_name in sql, f"Missing index: {index_name}"


def test_handle_updated_at_trigger():
    sql = _sql()
    assert "CREATE OR REPLACE FUNCTION public.handle_updated_at()" in sql
    for table in UPDATED_AT_TABLES:
        assert f"BEFORE UPDATE ON public.{table}" in sql
        assert f"EXECUTE FUNCTION public.handle_updated_at()" in sql


def test_pgcrypto_extension():
    sql = _sql()
    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" in sql
