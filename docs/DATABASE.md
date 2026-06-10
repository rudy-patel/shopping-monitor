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
