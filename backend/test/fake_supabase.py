"""In-memory Supabase test double for router unit tests."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

from postgrest.exceptions import APIError

from services.profile_service import PROFILE_COLUMNS, PROFILE_DEFAULTS


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, store: "FakeSupabaseClient", table: str):
        self._store = store
        self._table = table
        self._select_cols: list[str] | None = None
        self._eq_filters: list[tuple[str, str]] = []
        self._in_filter: tuple[str, list[str]] | None = None
        self._limit: int | None = None
        self._insert_payload: dict | list | None = None
        self._update_payload: dict | None = None
        self._delete_mode = False
        self._mode: str | None = None
        self._force_duplicate_on_insert = False

    def select(self, columns: str):
        self._select_cols = [c.strip() for c in columns.split(",")]
        return self

    def eq(self, column: str, value: str):
        self._eq_filters.append((column, value))
        return self

    def in_(self, column: str, values: list[str]):
        self._in_filter = (column, values)
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

    def delete(self):
        self._delete_mode = True
        return self

    def execute(self) -> FakeResponse:
        if self._insert_payload is not None:
            return self._execute_insert()
        if self._delete_mode:
            return self._execute_delete()
        if self._update_payload is not None:
            return self._execute_update()
        return self._execute_select()

    def _table_rows(self) -> dict[str, dict]:
        return self._store._rows_for(self._table)

    def _project(self, row: dict) -> dict:
        if not self._select_cols or self._select_cols == ["*"]:
            return deepcopy(row)
        return {col: row.get(col) for col in self._select_cols if col in row}

    def _filter_rows(self, rows: list[dict]) -> list[dict]:
        filtered = rows
        for col, val in self._eq_filters:
            filtered = [row for row in filtered if row.get(col) == val]
        if self._in_filter is not None:
            col, values = self._in_filter
            value_set = set(values)
            filtered = [row for row in filtered if row.get(col) in value_set]
        if self._limit is not None:
            filtered = filtered[: self._limit]
        return filtered

    def _execute_select(self) -> FakeResponse:
        rows = list(self._table_rows().values())
        rows = self._filter_rows(rows)

        if self._mode == "maybe_single":
            return FakeResponse(deepcopy(rows[0]) if rows else None)
        if self._mode == "single":
            if not rows:
                raise APIError({"message": "Row not found", "code": "PGRST116"})
            return FakeResponse(deepcopy(rows[0]))
        return FakeResponse([deepcopy(row) for row in rows])

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat()

    def _execute_insert(self) -> FakeResponse:
        payload = self._insert_payload
        rows_payload = payload if isinstance(payload, list) else [payload]
        inserted_rows: list[dict] = []

        for item in rows_payload:
            assert isinstance(item, dict)
            row = deepcopy(item)
            now = self._now_iso()

            if self._table == "profiles":
                user_id = row["user_id"]
                if user_id in self._store.profiles or self._force_duplicate_on_insert:
                    raise APIError({"message": "duplicate key value", "code": "23505"})
                row = {**PROFILE_DEFAULTS, **row, "created_at": now, "updated_at": now}
                for col in PROFILE_COLUMNS:
                    row.setdefault(col, None)
                self._store.profiles[user_id] = row
            elif self._table == "products":
                product_id = row.setdefault("id", str(uuid4()))
                row.setdefault("created_at", now)
                row.setdefault("updated_at", now)
                self._store.products[product_id] = row
            elif self._table == "product_listings":
                listing_id = row.setdefault("id", str(uuid4()))
                row.setdefault("created_at", now)
                row.setdefault("updated_at", now)
                self._store.product_listings[listing_id] = row
            elif self._table == "price_history":
                history_id = self._store._next_price_history_id()
                row["id"] = history_id
                row.setdefault("observed_at", now)
                self._store.price_history[history_id] = row
            elif self._table == "notifications":
                notification_id = row.setdefault("id", str(uuid4()))
                row.setdefault("created_at", now)
                row.setdefault("payload", {})
                self._store.notifications[notification_id] = row
            else:
                raise ValueError(f"insert not supported for table: {self._table}")

            inserted_rows.append(row)

        if isinstance(payload, list):
            projected = [self._project(row) for row in inserted_rows]
            return FakeResponse(projected)
        return FakeResponse(self._project(inserted_rows[0]))

    def _execute_update(self) -> FakeResponse:
        assert self._update_payload is not None
        rows = self._table_rows()
        matches = self._filter_rows(list(rows.values()))
        if not matches:
            if self._mode == "single":
                raise APIError({"message": "Row not found", "code": "PGRST116"})
            return FakeResponse(None)

        updated_rows: list[dict] = []
        for row in matches:
            row.update(self._update_payload)
            if self._table in {"profiles", "products", "product_listings"}:
                row["updated_at"] = self._now_iso()
            updated_rows.append(row)

        if self._mode == "single":
            return FakeResponse(self._project(updated_rows[0]))
        return FakeResponse([self._project(row) for row in updated_rows])

    def _execute_delete(self) -> FakeResponse:
        rows = self._table_rows()
        matches = self._filter_rows(list(rows.values()))
        deleted: list[dict] = []
        for row in matches:
            row_id = row.get("id") or row.get("user_id")
            if row_id is None:
                continue
            if self._table == "products":
                self._store._cascade_delete_product(str(row_id))
            else:
                del rows[str(row_id)]
            deleted.append(deepcopy(row))
        return FakeResponse(deleted)


class FakeSupabaseClient:
    def __init__(self):
        self.profiles: dict[str, dict] = {}
        self.products: dict[str, dict] = {}
        self.product_listings: dict[str, dict] = {}
        self.price_history: dict[int, dict] = {}
        self.notifications: dict[str, dict] = {}
        self.force_duplicate_on_insert = False
        self._price_history_counter = 1

    def _next_price_history_id(self) -> int:
        value = self._price_history_counter
        self._price_history_counter += 1
        return value

    def _rows_for(self, table: str) -> dict[str, dict]:
        if table == "profiles":
            return self.profiles
        if table == "products":
            return self.products
        if table == "product_listings":
            return self.product_listings
        if table == "price_history":
            return self.price_history
        if table == "notifications":
            return self.notifications
        raise ValueError(f"unexpected table: {table}")

    def _cascade_delete_product(self, product_id: str) -> None:
        listing_ids = [
            lid
            for lid, row in self.product_listings.items()
            if row.get("product_id") == product_id
        ]
        for listing_id in listing_ids:
            self.product_listings.pop(listing_id, None)
            self.price_history = {
                hid: row
                for hid, row in self.price_history.items()
                if row.get("listing_id") != listing_id
            }
        self.notifications = {
            nid: row
            for nid, row in self.notifications.items()
            if row.get("product_id") != product_id
        }
        self.products.pop(product_id, None)

    def table(self, name: str) -> FakeQuery:
        query = FakeQuery(self, name)
        query._force_duplicate_on_insert = self.force_duplicate_on_insert
        return query
