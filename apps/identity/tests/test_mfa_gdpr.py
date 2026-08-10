"""Identity MFA + consent registry + GDPR tests."""

import pytest
import worldview_identity.main as main
from fastapi.testclient import TestClient


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


def _register(client, email="ana@example.com"):
    r = client.post(
        "/v1/auth/register",
        json={"email": email, "password": "supersecret1", "display_name": "Ana"},
    )
    assert r.status_code == 201
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_mfa_enroll_and_verify(client):
    headers = _register(client)
    enrolled = client.post("/v1/auth/mfa/enroll", headers=headers)
    assert enrolled.status_code == 200
    secret = enrolled.json()["secret"]
    assert enrolled.json()["verified"] is False

    import pyotp

    code = pyotp.TOTP(secret).now()
    ok = client.post("/v1/auth/mfa/verify", json={"code": code}, headers=headers)
    assert ok.status_code == 200
    assert ok.json()["verified"] is True

    bad = client.post("/v1/auth/mfa/verify", json={"code": "000000"}, headers=headers)
    assert bad.status_code == 401


def test_mfa_enroll_resets_and_requires_auth(client):
    # unauthenticated requests are rejected
    assert client.post("/v1/auth/mfa/enroll").status_code == 401

    headers = _register(client)
    first = client.post("/v1/auth/mfa/enroll", headers=headers).json()["secret"]
    second = client.post("/v1/auth/mfa/enroll", headers=headers).json()["secret"]
    assert first != second


def test_consent_registry(client):
    headers = _register(client)
    ok = client.post("/v1/users/me/consents", json={"policy_id": "privacy_v1"}, headers=headers)
    assert ok.status_code == 201
    assert ok.json()["policy_id"] == "privacy_v1"

    listed = client.get("/v1/users/me/consents", headers=headers)
    assert [c["policy_id"] for c in listed.json()] == ["privacy_v1"]

    # revoking consent removes the record
    revoked = client.post(
        "/v1/users/me/consents",
        json={"policy_id": "privacy_v1", "accepted": False},
        headers=headers,
    )
    assert revoked.status_code == 201
    listed2 = client.get("/v1/users/me/consents", headers=headers)
    assert listed2.json() == []


def test_gdpr_export_and_delete(client):
    headers = _register(client)
    client.post("/v1/users/me/consents", json={"policy_id": "privacy_v1"}, headers=headers)

    exported = client.post("/v1/users/me/gdpr/export", headers=headers)
    assert exported.status_code == 200
    body = exported.json()
    assert body["status"] == "ready"
    assert body["data"]["user"]["email"] == "ana@example.com"
    assert [c["policy_id"] for c in body["data"]["consents"]] == ["privacy_v1"]

    deleted = client.post("/v1/users/me/gdpr/delete", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "completed"

    me = client.get("/v1/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"].endswith("deleted.worldview.vr")
    assert me.json()["display_name"] == "[deleted account]"


def test_gdpr_top_level_aliases(client):
    headers = _register(client)
    exported = client.post("/v1/gdpr/export", headers=headers)
    assert exported.status_code == 200
    assert exported.json()["status"] == "ready"

    deleted = client.post("/v1/gdpr/delete", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "completed"
