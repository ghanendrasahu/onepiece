"""Notification service tests: subscribe upsert, test push, auth."""

import pytest
import worldview_notifications.main as main
from fastapi.testclient import TestClient
from ulid import new as new_ulid


@pytest.fixture
def client(tmp_path, monkeypatch):
    from worldview.testing import test_database_url, truncate_all

    url = test_database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    from worldview.config import reset_settings

    reset_settings()
    from importlib import reload

    reload(main)
    with TestClient(main.app) as c:
        truncate_all(url)
        yield c


def _token(user_id: str | None = None, scopes=("user",)):
    from worldview.auth import create_access_token

    return create_access_token(user_id or str(new_ulid()), scopes=list(scopes))


def _auth(user_id: str | None = None, scopes=("user",)):
    return {"Authorization": f"Bearer {_token(user_id, scopes)}"}


def test_subscribe_creates_subscription(client):
    r = client.post(
        "/v1/notifications/subscribe",
        json={
            "push_token": "tok-1",
            "platform": "apns",
            "topics": ["creator.live", "tip.received"],
        },
        headers=_auth(),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["platform"] == "apns"
    assert "creator.live" in body["topics"]


def test_subscribe_upserts_same_token(client):
    user = str(new_ulid())
    headers = _auth(user)
    first = client.post(
        "/v1/notifications/subscribe",
        json={"push_token": "tok-2", "platform": "fcm", "topics": ["creator.live"]},
        headers=headers,
    )
    second = client.post(
        "/v1/notifications/subscribe",
        json={"push_token": "tok-2", "platform": "web", "topics": ["booking.confirmed"]},
        headers=headers,
    )
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["platform"] == "web"
    assert second.json()["topics"] == ["booking.confirmed"]


def test_subscribe_validates_platform(client):
    r = client.post(
        "/v1/notifications/subscribe",
        json={"push_token": "t", "platform": "sms", "topics": []},
        headers=_auth(),
    )
    assert r.status_code == 422


def test_test_notification_logs_delivery(client):
    user = str(new_ulid())
    headers = _auth(user)
    client.post(
        "/v1/notifications/subscribe",
        json={"push_token": "tok-3", "platform": "fcm"},
        headers=headers,
    )
    r = client.post("/v1/notifications/test", json={"topic": "creator.live"}, headers=headers)
    assert r.status_code == 201
    assert r.json()["topic"] == "creator.live"
    assert r.json()["status"] == "sent"


def test_test_notification_requires_auth(client):
    r = client.post("/v1/notifications/test", json={"topic": "creator.live"})
    assert r.status_code == 401
