"""Profile router unit tests."""

from __future__ import annotations

import os
from copy import deepcopy
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from core.settings import clear_settings_cache
from routers.profile import router as profile_router
from services.profile_service import PROFILE_COLUMNS, PROFILE_DEFAULTS

DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, store: dict[str, dict], table: str):
        self._store = store
        self._table = table
        self._select_cols: list[str] | None = None
        self._eq_col: str | None = None
        self._eq_val: str | None = None
        self._limit: int | None = None
        self._insert_payload: dict | list | None = None
        self._update_payload: dict | None = None
        self._mode: str | None = None
        self._force_duplicate_on_insert = False

    def select(self, columns: str):
        self._select_cols = [c.strip() for c in columns.split(",")]
        return self

    def eq(self, column: str, value: str):
        self._eq_col = column
        self._eq_val = value
        return self

    def limit(self, count: int):
        self._limit = count
        return self

    def maybe_single(self):
        self._mode = "maybe_single"
        return self

    def single(self):
        self._mode = "single"
        return self

    def insert(self, payload: dict | list):
        self._insert_payload = payload
        return self

    def update(self, payload: dict):
        self._update_payload = payload
        return self

    def execute(self) -> FakeResponse:
        if self._insert_payload is not None:
            return self._execute_insert()
        if self._update_payload is not None:
            return self._execute_update()
        return self._execute_select()

    def _project(self, row: dict) -> dict:
        if not self._select_cols:
            return deepcopy(row)
        return {col: row[col] for col in self._select_cols if col in row}

    def _execute_select(self) -> FakeResponse:
        rows = list(self._store.values())
        if self._eq_col and self._eq_val is not None:
            rows = [row for row in rows if row.get(self._eq_col) == self._eq_val]
        if self._limit is not None:
            rows = rows[: self._limit]

        if self._mode == "maybe_single":
            return FakeResponse(deepcopy(rows[0]) if rows else None)
        if self._mode == "single":
            if not rows:
                raise APIError({"message": "Row not found", "code": "PGRST116"})
            return FakeResponse(deepcopy(rows[0]))
        return FakeResponse([deepcopy(row) for row in rows])

    def _execute_insert(self) -> FakeResponse:
        payload = self._insert_payload
        assert isinstance(payload, dict)
        user_id = payload["user_id"]
        if user_id in self._store or self._force_duplicate_on_insert:
            raise APIError({"message": "duplicate key value", "code": "23505"})

        now = datetime.now(UTC).isoformat()
        row = {
            **PROFILE_DEFAULTS,
            **payload,
            "created_at": now,
            "updated_at": now,
        }
        for col in PROFILE_COLUMNS:
            row.setdefault(col, None)
        self._store[user_id] = row
        return FakeResponse(self._project(row))

    def _execute_update(self) -> FakeResponse:
        assert self._update_payload is not None
        if self._eq_col != "user_id" or self._eq_val is None:
            raise AssertionError("update requires eq(user_id, ...)")

        row = self._store.get(self._eq_val)
        if row is None:
            if self._mode == "single":
                raise APIError({"message": "Row not found", "code": "PGRST116"})
            return FakeResponse(None)

        row.update(self._update_payload)
        row["updated_at"] = datetime.now(UTC).isoformat()
        return FakeResponse(self._project(row))


class FakeSupabaseClient:
    def __init__(self):
        self.profiles: dict[str, dict] = {}
        self.force_duplicate_on_insert = False

    def table(self, name: str) -> FakeQuery:
        if name != "profiles":
            raise ValueError(f"unexpected table: {name}")
        query = FakeQuery(self.profiles, name)
        query._force_duplicate_on_insert = self.force_duplicate_on_insert
        return query


def make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(profile_router)
    return app


@pytest.fixture
def auth_env(monkeypatch):
    snapshot = dict(os.environ)
    monkeypatch.setattr("core.settings._env_file_path", lambda: None)
    clear_settings_cache()
    yield monkeypatch
    os.environ.clear()
    os.environ.update(snapshot)
    clear_settings_cache()


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeSupabaseClient()
    monkeypatch.setattr("services.profile_service.get_client", lambda: client)
    return client


@pytest.fixture
def profile_client(auth_env, fake_client, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "true")
    clear_settings_cache()
    return TestClient(make_app()), fake_client


def _seed_profile(fake: FakeSupabaseClient, user_id: str, **overrides) -> dict:
    now = datetime.now(UTC).isoformat()
    row = {
        **PROFILE_DEFAULTS,
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
        **overrides,
    }
    fake.profiles[user_id] = row
    return row


def test_get_profile_upserts_defaults_for_new_user(profile_client):
    client, fake = profile_client

    response = client.get("/api/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == DEV_USER_ID
    assert body["display_currency"] == "CAD"
    assert body["default_threshold_pct"] == 20
    assert body["theme"] == "light"
    assert len(fake.profiles) == 1


def test_get_profile_is_idempotent(profile_client):
    client, fake = profile_client

    first = client.get("/api/profile")
    second = client.get("/api/profile")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(fake.profiles) == 1


def test_get_profile_returns_existing_row_when_present(profile_client):
    client, fake = profile_client
    _seed_profile(fake, DEV_USER_ID, display_currency="USD", default_threshold_pct=15)

    response = client.get("/api/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["display_currency"] == "USD"
    assert body["default_threshold_pct"] == 15
    assert len(fake.profiles) == 1


def test_get_profile_concurrent_insert_recovers(profile_client):
    client, fake = profile_client
    _seed_profile(fake, DEV_USER_ID, display_currency="EUR")
    fake.force_duplicate_on_insert = True

    response = client.get("/api/profile")

    assert response.status_code == 200
    assert response.json()["display_currency"] == "EUR"
    assert len(fake.profiles) == 1


def test_patch_profile_updates_supplied_fields_only(profile_client):
    client, _fake = profile_client
    client.get("/api/profile")

    response = client.patch("/api/profile", json={"display_currency": "USD"})

    assert response.status_code == 200
    body = response.json()
    assert body["display_currency"] == "USD"
    assert body["default_threshold_pct"] == 20


def test_patch_profile_creates_then_updates(profile_client):
    client, fake = profile_client

    response = client.patch("/api/profile", json={"display_currency": "GBP"})

    assert response.status_code == 200
    assert response.json()["display_currency"] == "GBP"
    assert DEV_USER_ID in fake.profiles


def test_patch_profile_empty_body_returns_400(profile_client):
    client, _fake = profile_client
    client.get("/api/profile")

    response = client.patch("/api/profile", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "No fields to update"


@pytest.mark.parametrize(
    ("payload", "loc"),
    [
        ({"display_currency": "XYZ"}, "display_currency"),
        ({"default_threshold_pct": 0}, "default_threshold_pct"),
        ({"default_threshold_pct": 96}, "default_threshold_pct"),
        ({"theme": "rainbow"}, "theme"),
        ({"revisit_stale_days": 6}, "revisit_stale_days"),
        ({"revisit_stale_days": 366}, "revisit_stale_days"),
        ({"foo": 1}, "foo"),
    ],
)
def test_patch_profile_validation_errors(profile_client, payload, loc):
    client, _fake = profile_client
    client.get("/api/profile")

    response = client.patch("/api/profile", json=payload)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(err["loc"][-1] == loc for err in errors)


def test_requires_auth_when_bypass_disabled(auth_env, fake_client, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "false")
    clear_settings_cache()
    client = TestClient(make_app())

    response = client.get("/api/profile")

    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"
