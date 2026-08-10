"""Streaming realtime chat, presence, and tour-event tests."""

import pytest
import worldview_streaming.main as main
from fastapi.testclient import TestClient
from ulid import new as new_ulid


@pytest.fixture
def client(tmp_path, monkeypatch):
    from worldview.testing import test_database_url, truncate_all

    url = test_database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("REDIS_URL", "")
    from worldview.config import reset_settings

    reset_settings()
    from importlib import reload

    reload(main)
    import worldview_streaming.realtime as realtime

    realtime.get_room_hub.cache_clear()
    with TestClient(main.app) as c:
        truncate_all(url)
        yield c


def _token():
    from worldview.auth import create_access_token

    return create_access_token(str(new_ulid()), scopes=["user"])


def _drain(ws, type_name, max_frames=10):
    for _ in range(max_frames):
        frame = ws.receive_json()
        if frame["type"] == type_name:
            return frame
    return None


def test_room_chat_broadcast(client):
    with client.websocket_connect(f"/v1/tours/tour-1/chat?access_token={_token()}") as a:
        a.receive_json()  # presence.sync
        a.receive_json()  # chat.history
        a.receive_json()  # conn.ready

        with client.websocket_connect(f"/v1/tours/tour-1/chat?access_token={_token()}") as b:
            presence = b.receive_json()  # presence.sync (sees a)
            b.receive_json()  # chat.history
            b.receive_json()  # conn.ready
            _drain(b, "presence.sync")  # post-join presence broadcast
            assert len(presence["members"]) == 2

            a.send_json({"type": "chat.send", "body": "ciao!"})
            # a also receives its own echo before b; drain a, then read from b
            while True:
                frame = b.receive_json()
                if frame["type"] == "chat.msg":
                    break
            assert frame["body"] == "ciao!"
            assert frame["mod_flags"] == []
            assert "msg_id" in frame and "t" in frame


def test_chat_moderation_blocks_profanity(client):
    with client.websocket_connect(f"/v1/tours/tour-1/chat?access_token={_token()}") as a:
        a.receive_json()
        a.receive_json()
        a.receive_json()
        a.send_json({"type": "chat.send", "body": "kurwa bad word"})
        rejected = _drain(a, "chat.rejected")
        assert rejected is not None
        assert rejected["reason"] == "blocked"


def test_chat_moderation_flags_contact_for_review(client):
    with client.websocket_connect(f"/v1/tours/tour-1/chat?access_token={_token()}") as a:
        a.receive_json()
        a.receive_json()
        a.receive_json()
        a.send_json({"type": "chat.send", "body": "join my telegram.me/xyz group"})
        frame = _drain(a, "chat.msg")
        assert frame is not None
        assert "review" in frame["mod_flags"]


def test_chat_reaction_and_watch_sync_echo(client):
    with client.websocket_connect(f"/v1/tours/tour-1/chat?access_token={_token()}") as a:
        a.receive_json()
        a.receive_json()
        a.receive_json()

        a.send_json({"type": "chat.reaction", "msg_id": "m1", "emoji": "👍"})
        reaction = _drain(a, "chat.reaction")
        assert reaction is not None and reaction["msg_id"] == "m1"

        a.send_json({"type": "watch.sync", "tour_id": "tour-1", "t": 12.5, "playState": "play"})
        watch = _drain(a, "watch.sync")
        assert watch is not None and watch["t"] == 12.5


def test_chat_requires_auth(client):
    with client.websocket_connect("/v1/tours/tour-1/chat") as ws:
        frame = ws.receive_json()
        assert frame["type"] == "error"
        assert frame["detail"] == "authentication required"


def test_chat_history_persists_in_hub(client):
    with client.websocket_connect(f"/v1/tours/tour-2/chat?access_token={_token()}") as a:
        a.receive_json()
        a.receive_json()
        a.receive_json()
        a.send_json({"type": "chat.send", "body": "saved?"})

    with client.websocket_connect(f"/v1/tours/tour-2/chat?access_token={_token()}") as b:
        b.receive_json()  # presence.sync
        history = b.receive_json()  # chat.history
        assert history["type"] == "chat.history"
        assert [m["body"] for m in history["messages"]] == ["saved?"]
        b.receive_json()  # conn.ready


def test_stream_lifecycle_emits_events(client):
    from worldview.auth import create_access_token

    claims_user = str(new_ulid())
    headers = {"Authorization": f"Bearer {create_access_token(claims_user, scopes=['user'])}"}
    created = client.post("/v1/streams", json={}, headers=headers)
    stream_id = created.json()["id"]

    with client.websocket_connect(f"/v1/streams/{stream_id}/events?access_token={_token()}") as ws:
        snapshot = ws.receive_json()
        assert snapshot["type"] == "stream.snapshot"

        client.post(f"/v1/streams/{stream_id}/start", headers=headers)
        event = ws.receive_json()
        assert event["type"] == "stream.state"
        assert event["status"] == "live"
        assert "viewers" in event  # doc 06 §7 stream.state payload
