"""Health endpoint unit tests."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "running" in response.json()["message"].lower()


def test_health_head():
    response = client.head("/health")
    assert response.status_code == 200


def test_health_get():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "shopping-monitor-api"
    assert body["status"] in ("healthy", "degraded")
