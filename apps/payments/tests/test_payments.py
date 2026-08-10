"""Payments service API tests: plans, checkout, tips, purchases, webhook."""

import pytest
import worldview_payments.main as main
from fastapi.testclient import TestClient
from ulid import new as new_ulid


@pytest.fixture
def client(tmp_path, monkeypatch):
    from worldview.testing import test_database_url, truncate_all

    url = test_database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")
    monkeypatch.setenv("CATALOG_SERVICE_URL", "http://catalog.test")
    from worldview.config import reset_settings

    reset_settings()
    from importlib import reload

    reload(main)
    with TestClient(main.app) as c:
        truncate_all(url)
        yield c


def _token(user_id: str | None = None):
    from worldview.auth import create_access_token

    return create_access_token(user_id or str(new_ulid()), scopes=["user"])


def _auth(user_id: str | None = None):
    return {"Authorization": f"Bearer {_token(user_id)}"}


def test_list_plans(client):
    r = client.get("/v1/billing/plans")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert "free" in ids and "pro" in ids and "creator" in ids


def test_checkout_in_mock_mode(client):
    r = client.post("/v1/billing/checkout", json={"plan_id": "pro"}, headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["checkout_url"].startswith("https://checkout.worldview.vr/mock")
    assert body["provider_checkout_id"].startswith("cs_mock")


def test_checkout_unknown_plan(client):
    r = client.post("/v1/billing/checkout", json={"plan_id": "nope"}, headers=_auth())
    assert r.status_code == 404


def test_customer_portal(client):
    r = client.post("/v1/billing/portal", headers=_auth())
    assert r.status_code == 200
    assert "/mock/portal/" in r.json()["portal_url"]


def test_tip_and_idempotency(client, monkeypatch):
    from worldview.auth import create_access_token

    creator = str(new_ulid())
    user = str(new_ulid())
    monkeypatch.setattr(
        "worldview_payments.catalog_client.resolve_stream_creator",
        lambda stream_id: creator,
    )
    headers = {"Authorization": f"Bearer {create_access_token(user, scopes=['user'])}"}
    r = client.post(
        "/v1/tips/s-123",
        json={"cents": 500, "message": "great tour", "idempotency_key": "k-1"},
        headers=headers,
    )
    assert r.status_code == 201
    tip_id = r.json()["id"]

    r2 = client.post(
        "/v1/tips/s-123",
        json={"cents": 500, "message": "great tour", "idempotency_key": "k-1"},
        headers=headers,
    )
    assert r2.status_code == 201
    assert r2.json()["id"] == tip_id  # idempotent replay returns the same tip


def test_tip_unknown_stream(client, monkeypatch):
    from worldview.auth import create_access_token

    user = str(new_ulid())
    monkeypatch.setattr(
        "worldview_payments.catalog_client.resolve_stream_creator",
        lambda stream_id: None,
    )
    headers = {"Authorization": f"Bearer {create_access_token(user, scopes=['user'])}"}
    r = client.post("/v1/tips/s-missing", json={"cents": 100}, headers=headers)
    assert r.status_code == 404


def test_purchase_tour_records_transaction(client, monkeypatch):
    from worldview.auth import create_access_token

    user = str(new_ulid())
    monkeypatch.setattr(
        "worldview_payments.catalog_client.resolve_tour_price",
        lambda tour_id: 999,
    )
    headers = {"Authorization": f"Bearer {create_access_token(user, scopes=['user'])}"}
    r = client.post("/v1/tours/t-1/purchase", headers=headers)
    assert r.status_code == 201
    assert r.json()["gross_cents"] == 999
    assert r.json()["status"] == "succeeded"

    purchases = client.get("/v1/purchases", headers=headers)
    assert len(purchases.json()) == 1
    assert purchases.json()[0]["type"] == "pay_per_tour"


def test_stripe_webhook_acknowledged(client):
    event = {
        "id": "evt_1",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_x",
                "subscription": "sub_1",
                "metadata": {"plan_id": "pro"},
            }
        },
    }
    r = client.post("/v1/webhooks/stripe", json=event)
    assert r.status_code == 200
    assert r.json() == {"received": True}
