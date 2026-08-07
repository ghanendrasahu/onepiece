"""Streaming service API tests."""

import pytest
import worldview_streaming.main as main
from fastapi.testclient import TestClient
from ulid import new as new_ulid


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'stream.db'}")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    from worldview.config import reset_settings

    reset_settings()
    from importlib import reload

    reload(main)
    with TestClient(main.app) as c:
        yield c


def _auth_headers():
    from worldview.auth import create_access_token

    return {"Authorization": f"Bearer {create_access_token(str(new_ulid()), scopes=['user'])}"}


def test_full_lifecycle(client):
    headers = _auth_headers()
    created = client.post("/v1/streams", json={}, headers=headers)
    assert created.status_code == 201
    stream_id = created.json()["id"]
    assert created.json()["status"] == "preparing"

    assert client.post(f"/v1/streams/{stream_id}/start", headers=headers).json()["status"] == "live"
    assert (
        client.post(f"/v1/streams/{stream_id}/pause", headers=headers).json()["status"] == "paused"
    )
    assert (
        client.post(f"/v1/streams/{stream_id}/resume", headers=headers).json()["status"] == "live"
    )
    assert client.post(f"/v1/streams/{stream_id}/end", headers=headers).json()["status"] == "ended"

    live = client.get("/v1/streams/live")
    assert all(s["status"] == "live" for s in live.json())


def test_invalid_transition_conflicts(client):
    headers = _auth_headers()
    stream_id = client.post("/v1/streams", json={}, headers=headers).json()["id"]
    r = client.post(f"/v1/streams/{stream_id}/pause", headers=headers)
    assert r.status_code == 409


def test_creator_authorization(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'stream2.db'}")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    from worldview.config import reset_settings

    reset_settings()
    from importlib import reload

    reload(main)
    with TestClient(main.app) as c:
        headers_a = _auth_headers()
        stream_id = c.post("/v1/streams", json={}, headers=headers_a).json()["id"]
        headers_b = _auth_headers()
        r = c.post(f"/v1/streams/{stream_id}/start", headers=headers_b)
        assert r.status_code == 403


def test_get_missing_stream(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'stream3.db'}")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    from worldview.config import reset_settings

    reset_settings()
    from importlib import reload

    reload(main)
    with TestClient(main.app) as c:
        assert c.get("/v1/streams/nonexistent").status_code == 404
