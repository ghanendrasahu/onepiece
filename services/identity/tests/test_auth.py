"""Identity service API tests."""

import pytest
from fastapi.testclient import TestClient
from worldview_identity import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    from worldview.config import reset_settings

    reset_settings()
    from importlib import reload

    reload(main)
    with TestClient(main.app) as c:
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


def test_unauthorized_me(client):
    assert client.get("/v1/users/me").status_code == 401


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}
