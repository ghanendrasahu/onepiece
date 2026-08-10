"""Moderation service tests: reporting, admin queue, decisions, stream admin."""

import pytest
import worldview_moderation.main as main
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


def _seed_user(db, user_id: str, email: str):
    from worldview_identity.models import User

    db.add(
        User(
            id=user_id,
            email=email,
            password_hash="x",
            display_name="Tester",
            is_verified=True,
        )
    )


def _seed_stream(db, stream_id: str, creator_id: str):
    from worldview_streaming.models import StreamSession

    db.add(
        StreamSession(
            id=stream_id,
            creator_id=creator_id,
            status="live",
            quality_ladder="720p,1080p",
            spatial_audio=False,
        )
    )


def _session():
    from worldview.db import get_session_factory

    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def test_create_report_creates_queued_item(client):
    r = client.post(
        "/v1/reports",
        json={"object_type": "stream", "object_id": "s-123", "reason": "spam"},
        headers=_auth(),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["object_type"] == "stream"
    assert body["decision"] is None
    assert body["risk_score"] == 0.5


def test_report_deduplicates_per_reporter(client):
    headers = _auth()
    r1 = client.post(
        "/v1/reports", json={"object_type": "chat", "object_id": "chat-9"}, headers=headers
    )
    r2 = client.post(
        "/v1/reports", json={"object_type": "chat", "object_id": "chat-9"}, headers=headers
    )
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.json()["risk_score"] > r1.json()["risk_score"]


def test_report_requires_auth(client):
    r = client.post("/v1/reports", json={"object_type": "stream", "object_id": "s-1"})
    assert r.status_code == 401


def test_admin_queue_and_decision(client):
    from worldview.db import get_session_factory

    creator = str(new_ulid())
    reporter = str(new_ulid())
    with get_session_factory()() as db:
        _seed_user(db, reporter, "reporter@worldview.vr")
        _seed_user(db, creator, "creator@worldview.vr")
        _seed_stream(db, "s-adm", creator)
        db.commit()

    headers = _auth(reporter)
    r = client.post(
        "/v1/reports", json={"object_type": "stream", "object_id": "s-adm"}, headers=headers
    )
    item_id = r.json()["id"]

    queue = client.get("/v1/admin/moderation/queue", headers=_auth(scopes=("admin",)))
    ids = [i["id"] for i in queue.json()]
    assert item_id in ids

    decision = client.post(
        f"/v1/admin/moderation/{item_id}/decision",
        json={"decision": "removed", "note": "confirmed spam"},
        headers=_auth(scopes=("admin",)),
    )
    assert decision.status_code == 200
    assert decision.json()["decision"] == "removed"
    assert decision.json()["reviewed_by"] is not None

    empty = client.get("/v1/admin/moderation/queue", headers=_auth(scopes=("admin",)))
    assert item_id not in [i["id"] for i in empty.json()]


def test_admin_requires_scope(client):
    r = client.get("/v1/admin/moderation/queue", headers=_auth())
    assert r.status_code == 403


def test_admin_users_and_suspend(client):
    from worldview.db import get_session_factory

    target = str(new_ulid())
    with get_session_factory()() as db:
        _seed_user(db, target, "suspect@worldview.vr")
        db.commit()

    users = client.get("/v1/admin/users?q=suspect", headers=_auth(scopes=("admin",)))
    assert users.status_code == 200
    assert users.json()[0]["id"] == target
    assert users.json()[0]["status"] == "active"

    suspend = client.post(
        f"/v1/admin/users/{target}/suspend",
        json={"reason": "abuse", "duration_hours": 72},
        headers=_auth(scopes=("admin",)),
    )
    assert suspend.status_code == 200
    assert suspend.json()["status"] == "suspended"

    actions = client.get("/v1/admin/actions", headers=_auth(scopes=("admin",)))
    assert actions.json()[0]["action"] == "suspend"


def test_admin_streams_lists_sessions(client):
    from worldview.db import get_session_factory

    creator = str(new_ulid())
    with get_session_factory()() as db:
        _seed_user(db, creator, "creator2@worldview.vr")
        _seed_stream(db, "s-1", creator)
        _seed_stream(db, "s-2", creator)
        db.commit()

    streams = client.get("/v1/admin/streams", headers=_auth(scopes=("admin",)))
    assert streams.status_code == 200
    ids = [s["id"] for s in streams.json()]
    assert "s-1" in ids and "s-2" in ids
