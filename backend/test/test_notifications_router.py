"""Notification router unit tests."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.settings import clear_settings_cache
from routers.notifications import router as notifications_router
from test.fake_supabase import FakeSupabaseClient

DEV_USER_ID = "00000000-0000-0000-0000-000000000001"
OTHER_USER_ID = "00000000-0000-0000-0000-000000000002"


def make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(notifications_router)
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
    monkeypatch.setattr("services.notification_service.get_client", lambda: client)
    monkeypatch.setattr("services.product_service.get_client", lambda: client)
    monkeypatch.setattr("services.profile_service.get_client", lambda: client)
    return client


@pytest.fixture
def notifications_client(auth_env, fake_client, monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "true")
    clear_settings_cache()
    return TestClient(make_app()), fake_client


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _seed_product(
    fake: FakeSupabaseClient,
    *,
    user_id: str = DEV_USER_ID,
    title: str = "Seeded Product",
    status: str = "active",
) -> dict:
    product_id = str(uuid4())
    now = _now()
    row = {
        "id": product_id,
        "user_id": user_id,
        "title": title,
        "brand": "Brand",
        "image_url": None,
        "category": "tech",
        "category_source": "heuristic",
        "status": status,
        "notification_threshold_pct": None,
        "notifications_enabled": True,
        "discovery_status": "complete",
        "last_refresh_at": None,
        "last_user_interaction_at": None,
        "created_at": now,
        "updated_at": now,
    }
    fake.products[product_id] = row
    return row


def _seed_notification(
    fake: FakeSupabaseClient,
    *,
    user_id: str = DEV_USER_ID,
    product_id: str | None = None,
    notification_type: str = "discovery_complete",
    is_read: bool = False,
    payload: dict | None = None,
    created_at: str | None = None,
) -> dict:
    notification_id = str(uuid4())
    row = {
        "id": notification_id,
        "user_id": user_id,
        "product_id": product_id,
        "listing_id": None,
        "type": notification_type,
        "payload": payload or {},
        "is_read": is_read,
        "email_sent_at": None,
        "created_at": created_at or _now(),
    }
    fake.notifications[notification_id] = row
    return row


def test_list_empty(notifications_client):
    client, _fake = notifications_client

    response = client.get("/api/notifications")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["unread_count"] == 0
    assert body["total"] == 0


def test_list_newest_first(notifications_client, fake_client):
    client, fake = notifications_client
    product = _seed_product(fake)
    older = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    newer = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    older_row = _seed_notification(
        fake,
        product_id=product["id"],
        created_at=older,
        payload={"auto_added_count": 1, "needs_review_count": 0},
    )
    newer_row = _seed_notification(
        fake,
        product_id=product["id"],
        created_at=newer,
        notification_type="needs_input",
    )

    response = client.get("/api/notifications")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [newer_row["id"], older_row["id"]]


def test_list_pagination_load_more(notifications_client, fake_client):
    client, fake = notifications_client
    product = _seed_product(fake)
    base = datetime.now(UTC)
    for index in range(25):
        _seed_notification(
            fake,
            product_id=product["id"],
            created_at=(base - timedelta(minutes=index)).isoformat(),
            payload={"index": index},
        )

    page_one = client.get("/api/notifications", params={"limit": 10, "offset": 0})
    page_two = client.get("/api/notifications", params={"limit": 10, "offset": 10})

    assert page_one.status_code == 200
    assert page_two.status_code == 200
    body_one = page_one.json()
    body_two = page_two.json()
    assert len(body_one["items"]) == 10
    assert len(body_two["items"]) == 10
    assert body_one["total"] == 25
    assert body_two["total"] == 25
    assert {item["id"] for item in body_one["items"]}.isdisjoint(
        {item["id"] for item in body_two["items"]}
    )


def test_list_90_day_filter(notifications_client, fake_client):
    client, fake = notifications_client
    product = _seed_product(fake)
    old_cutoff = (datetime.now(UTC) - timedelta(days=91)).isoformat()
    recent = _now()
    _seed_notification(fake, product_id=product["id"], created_at=old_cutoff)
    recent_row = _seed_notification(fake, product_id=product["id"], created_at=recent)

    response = client.get("/api/notifications")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == recent_row["id"]


def test_list_enriches_product_title(notifications_client, fake_client):
    client, fake = notifications_client
    product = _seed_product(fake, title="Enriched Title")
    _seed_notification(fake, product_id=product["id"])

    response = client.get("/api/notifications")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["product_title"] == "Enriched Title"
    assert item["product_status"] == "active"


def test_unread_count_global(notifications_client, fake_client):
    client, fake = notifications_client
    product = _seed_product(fake)
    base = datetime.now(UTC)
    for index in range(12):
        _seed_notification(
            fake,
            product_id=product["id"],
            is_read=index >= 5,
            created_at=(base - timedelta(minutes=index)).isoformat(),
        )

    response = client.get("/api/notifications", params={"limit": 5, "offset": 5})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 5
    assert body["unread_count"] == 5


def test_mark_read_by_ids(notifications_client, fake_client):
    client, fake = notifications_client
    product = _seed_product(fake)
    row = _seed_notification(fake, product_id=product["id"], is_read=False)

    response = client.post(
        "/api/notifications/mark-read",
        json={"ids": [row["id"]]},
    )

    assert response.status_code == 200
    assert response.json()["updated_count"] == 1
    assert fake.notifications[row["id"]]["is_read"] is True


def test_mark_read_all(notifications_client, fake_client):
    client, fake = notifications_client
    product = _seed_product(fake)
    _seed_notification(fake, product_id=product["id"], is_read=False)
    _seed_notification(
        fake,
        product_id=product["id"],
        notification_type="needs_input",
        is_read=False,
    )
    _seed_notification(fake, product_id=product["id"], is_read=True)

    response = client.post("/api/notifications/mark-read", json={"all": True})

    assert response.status_code == 200
    assert response.json()["updated_count"] == 2
    assert all(row["is_read"] for row in fake.notifications.values())


def test_mark_read_updates_last_user_interaction(notifications_client, fake_client):
    client, fake = notifications_client
    product = _seed_product(fake)
    row = _seed_notification(fake, product_id=product["id"], is_read=False)
    assert product["last_user_interaction_at"] is None

    response = client.post(
        "/api/notifications/mark-read",
        json={"ids": [row["id"]]},
    )

    assert response.status_code == 200
    assert fake.products[product["id"]]["last_user_interaction_at"] is not None


def test_mark_read_ownership(notifications_client, fake_client):
    client, fake = notifications_client
    foreign = _seed_notification(fake, user_id=OTHER_USER_ID)

    response = client.post(
        "/api/notifications/mark-read",
        json={"ids": [foreign["id"]]},
    )

    assert response.status_code == 404


def test_action_keep(notifications_client, fake_client):
    client, fake = notifications_client
    product = _seed_product(fake)
    row = _seed_notification(
        fake,
        product_id=product["id"],
        notification_type="revisit_stale",
        is_read=False,
    )

    response = client.post(
        f"/api/notifications/{row['id']}/action",
        json={"action": "keep"},
    )

    assert response.status_code == 200
    assert response.json()["action"] == "keep"
    assert fake.notifications[row["id"]]["is_read"] is True
    assert fake.products[product["id"]]["last_user_interaction_at"] is not None


def test_action_archive(notifications_client, fake_client):
    client, fake = notifications_client
    product = _seed_product(fake)
    row = _seed_notification(
        fake,
        product_id=product["id"],
        notification_type="revisit_on_sale",
        is_read=False,
        payload={"drop_pct": 0.2},
    )

    response = client.post(
        f"/api/notifications/{row['id']}/action",
        json={"action": "archive"},
    )

    assert response.status_code == 200
    assert response.json()["action"] == "archive"
    assert fake.products[product["id"]]["status"] == "archived"
    assert fake.notifications[row["id"]]["is_read"] is True


def test_action_invalid_type(notifications_client, fake_client):
    client, fake = notifications_client
    product = _seed_product(fake)
    row = _seed_notification(
        fake,
        product_id=product["id"],
        notification_type="discovery_complete",
        payload={"auto_added_count": 1, "needs_review_count": 0},
    )

    response = client.post(
        f"/api/notifications/{row['id']}/action",
        json={"action": "archive"},
    )

    assert response.status_code == 400


def test_list_unread_only_keeps_global_unread_count(notifications_client, fake_client):
    client, fake = notifications_client
    product = _seed_product(fake)
    _seed_notification(fake, product_id=product["id"], is_read=False)
    _seed_notification(
        fake,
        product_id=product["id"],
        notification_type="needs_input",
        is_read=True,
    )

    response = client.get("/api/notifications", params={"unread_only": True})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["unread_count"] == 1


def test_mark_read_idempotent(notifications_client, fake_client):
    client, fake = notifications_client
    product = _seed_product(fake)
    row = _seed_notification(fake, product_id=product["id"], is_read=True)

    response = client.post(
        "/api/notifications/mark-read",
        json={"ids": [row["id"]]},
    )

    assert response.status_code == 200
    assert response.json()["updated_count"] == 0


def test_action_archive_already_archived(notifications_client, fake_client):
    client, fake = notifications_client
    product = _seed_product(fake, status="archived")
    row = _seed_notification(
        fake,
        product_id=product["id"],
        notification_type="revisit_on_sale",
        is_read=False,
    )

    response = client.post(
        f"/api/notifications/{row['id']}/action",
        json={"action": "archive"},
    )

    assert response.status_code == 400
