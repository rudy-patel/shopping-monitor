# Database Specification

Schema and security conventions for **shopping-monitor** (Supabase PostgreSQL).

## Overview

The app uses **Supabase PostgreSQL** with Supabase Auth. Document every table here as you add migrations under `backend/db/migrations/`.

```
┌─────────────────┐
│   auth.users    │  (Supabase managed)
│  (Supabase)     │
└─────────────────┘
```

No application tables yet. Add migrations starting at `001_*.sql`.

---

## Row Level Security (RLS)

**Every new table in `public` must enable RLS in the same migration** (or an immediately applied follow-up). Never ship tables without RLS.

### Pattern A: User-owned data (client + API)

```sql
ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own rows"
    ON my_table FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own rows"
    ON my_table FOR UPDATE
    USING (auth.uid() = user_id);
```

**Note:** UPDATE requires a SELECT policy in Postgres RLS or updates silently affect 0 rows.

### Pattern B: Backend-only (service role)

```sql
ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;
-- No policies for authenticated / anon — PostgREST denies direct client access.
-- FastAPI uses SUPABASE_SERVICE_ROLE_KEY for server-side queries.
```

Use Pattern B when all reads/writes go through the API and the browser must not query the table directly.

### Supabase schema checklist

Before opening a PR that adds or changes Supabase schema:

1. Enable RLS on every new `public` table in the same migration.
2. Choose the narrowest access model:
   - Pattern A for user-owned rows the browser/API may read by user.
   - Pattern B for backend-only tables such as caches, job state, advisory-lock helpers, or operational metadata.
3. Never use `user_metadata` for authorization decisions. Use `auth.uid()`, app-owned tables, or trusted `app_metadata` only when necessary.
4. Keep `SUPABASE_SERVICE_ROLE_KEY` server-only; frontend code may only use the publishable/anon key.
5. Add indexes for every expected ownership join and high-volume filter (`user_id`, `product_id`, `listing_id`, status fields, and timestamp windows).
6. Use `TIMESTAMPTZ` for timestamps and integer cents for money.
7. If creating views in an exposed schema, use `security_invoker = true` where supported or keep the view out of exposed schemas.
8. Update this document's table list and migration list in the same change.

---

## Extending the Schema

When adding features:

1. **New tables** should reference `auth.users(id)` or a `profiles` table for ownership.
2. **Always enable RLS** (see patterns above).
3. **Use TIMESTAMPTZ** for all timestamp columns.
4. **Add indexes** for frequently queried columns.
5. **Document** all new tables and columns in this file.
6. **Create migrations** in `backend/db/migrations/` with sequential `NNN_snake_case.sql` names.
7. **Reference each migration filename** in this doc (required by `scripts/check_migrations.py` in CI).

### Test data (integration tests)

When integration tests need DB access:

- Use dedicated `test_*` tables or isolated rows with a run-specific prefix.
- Tear down only data created by the test (avoid deleting shared CI fixtures).
- Mark tests with `@pytest.mark.integration`.

---

## Migrations

| File | Description |
|------|-------------|
| _(none yet)_ | Add `001_*.sql` when schema work begins |
