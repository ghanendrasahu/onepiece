"""Identity service API tests."""

import pytest
from fastapi.testclient import TestClient
from worldview_identity import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    from worldview.testing import test_database_url, truncate_all

    monkeypatch.setenv("DATABASE_URL", test_database_url(tmp_path))
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    from worldview.config import reset_settings

    reset_settings()
    from importlib import reload

    reload(main)
    with TestClient(main.app) as c:
        truncate_all(test_database_url(tmp_path))
        yield c


def test_register_and_login(client):
    r = client.post(
        "/v1/auth/register",
        json={"email": "a@b.com", "password": "supersecret1", "display_name": "Ana"},
    )
    assert r.status_code == 201
    token = r.json()["access_token"]

    me = client.get("/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "a@b.com"

    login = client.post("/v1/auth/login", json={"email": "a@b.com", "password": "supersecret1"})
    assert login.status_code == 200


def test_duplicate_register_conflicts(client):
    payload = {"email": "x@y.com", "password": "supersecret1", "display_name": "X"}
    assert client.post("/v1/auth/register", json=payload).status_code == 201
    assert client.post("/v1/auth/register", json=payload).status_code == 409


def test_login_wrong_password(client):
    client.post(
        "/v1/auth/register",
        json={"email": "w@x.com", "password": "supersecret1", "display_name": "W"},
    )
    r = client.post("/v1/auth/login", json={"email": "w@x.com", "password": "wrongpass1"})
    assert r.status_code == 401


def test_social_login_provisions_user(client):
    r = client.post(
        "/v1/auth/login",
        json={"email": "social@x.com", "provider": "google", "code": "dev-social-code"},
    )
    assert r.status_code == 200
    assert r.json()["user_id"]

    me = client.get("/v1/users/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "social@x.com"


def test_social_login_reuses_existing_user(client):
    client.post(
        "/v1/auth/register",
        json={"email": "again@x.com", "password": "supersecret1", "display_name": "Again"},
    )
    r = client.post(
        "/v1/auth/login",
        json={"email": "again@x.com", "provider": "apple", "code": "dev-social-code"},
    )
    assert r.status_code == 200


def test_social_login_rejects_bad_code(client):
    r = client.post(
        "/v1/auth/login",
        json={"email": "bad@x.com", "provider": "google", "code": "nope"},
    )
    assert r.status_code == 401


def test_social_login_requires_code(client):
    r = client.post("/v1/auth/login", json={"email": "noc@x.com", "provider": "google"})
    assert r.status_code == 422


def test_unauthorized_me(client):
    assert client.get("/v1/users/me").status_code == 401


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_refresh_rotates_and_revocation(client):
    r = client.post(
        "/v1/auth/register",
        json={"email": "r@z.com", "password": "supersecret1", "display_name": "R"},
    )
    assert r.status_code == 201
    body = r.json()
    old_refresh = body["refresh_token"]

    refreshed = client.post("/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert refreshed.status_code == 200
    new_body = refreshed.json()
    assert new_body["access_token"]
    # Old refresh token is rotated and must no longer work.
    replay = client.post("/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert replay.status_code == 401

    # Logout revokes the session; the rotated refresh is rejected afterwards.
    logout = client.post(
        "/v1/auth/logout", headers={"Authorization": f"Bearer {new_body['access_token']}"}
    )
    assert logout.status_code == 200
    after_logout = client.post(
        "/v1/auth/refresh", json={"refresh_token": new_body["refresh_token"]}
    )
    assert after_logout.status_code == 401


def test_refresh_rejects_garbage_token(client):
    r = client.post("/v1/auth/refresh", json={"refresh_token": "not-a-valid-token"})
    assert r.status_code == 401


def test_patch_profile_updates_fields(client):
    r = client.post(
        "/v1/auth/register",
        json={"email": "patch@b.com", "password": "supersecret1", "display_name": "Pat"},
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    patch = client.patch(
        "/v1/users/me",
        json={
            "display_name": "Patricia",
            "avatar": "https://cdn.worldview.vr/avatars/p1.jpg",
            "accessibility": {"reduced_motion": True, "subtitles": True},
            "locale": "fr",
        },
        headers=headers,
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["display_name"] == "Patricia"
    assert body["avatar_url"] == "https://cdn.worldview.vr/avatars/p1.jpg"
    assert body["accessibility"] == {"reduced_motion": True, "subtitles": True}
    assert body["locale"] == "fr"


def test_devices_list_and_revoke(client):
    r = client.post(
        "/v1/auth/register",
        json={"email": "dev@b.com", "password": "supersecret1", "display_name": "Dev"},
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/v1/auth/logout", headers=headers)  # creates a session row via refresh? no-op
    r2 = client.post(
        "/v1/auth/register",
        json={"email": "d2@b.com", "password": "supersecret1", "display_name": "D2"},
    )
    token2 = r2.json()["access_token"]

    devices = client.get("/v1/users/me/devices", headers={"Authorization": f"Bearer {token2}"})
    assert devices.status_code == 200

    revoke = client.delete(
        "/v1/users/me/devices/not-my-device",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert revoke.status_code == 404
