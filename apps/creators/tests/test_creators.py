"""Creator platform service tests: apply, verify, dashboard, streams, loans, payouts."""

import pytest
import worldview_creators.main as main
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


def _seed_stream(db, stream_id: str, creator_id: str, status: str = "live"):
    from worldview_streaming.models import StreamSession

    db.add(
        StreamSession(
            id=stream_id,
            creator_id=creator_id,
            status=status,
            quality_ladder="720p,1080p",
            spatial_audio=False,
        )
    )


def _seed_tip(db, tip_id: str, creator_id: str, cents: int):
    from worldview_payments.models import Tip

    db.add(
        Tip(
            id=tip_id,
            stream_id="s-1",
            from_user=str(new_ulid()),
            to_creator=creator_id,
            cents=cents,
        )
    )


def _seed_payout(
    db, payout_id: str, creator_id: str, cents: int, status: str = "pending", **kwargs
):
    from worldview_creators.models import Payout

    db.add(
        Payout(
            id=payout_id,
            creator_id=creator_id,
            amount_cents=cents,
            currency="USD",
            status=status,
            **kwargs,
        )
    )


def test_apply_creates_profile(client):
    r = client.post(
        "/v1/creators/apply",
        json={"equipment": ["insta360-x4"], "region": "Tokyo", "id_doc_token": "id-1"},
        headers=_auth(),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "applied"
    assert body["region"] == "Tokyo"
    assert body["equipment"] == "insta360-x4"


def test_verify_after_apply(client):
    user = str(new_ulid())
    client.post(
        "/v1/creators/apply",
        json={"equipment": [], "region": "Paris", "id_doc_token": "id-2"},
        headers=_auth(user),
    )
    r = client.post("/v1/creators/verify", json={"liveness_token": "lv-1"}, headers=_auth(user))
    assert r.status_code == 200
    assert r.json()["status"] == "verified"
    assert r.json()["verified_at"] is not None


def test_verify_requires_profile(client):
    r = client.post("/v1/creators/verify", json={"liveness_token": "lv-x"}, headers=_auth())
    assert r.status_code == 404


def test_verify_rejects_failed_geocheck(client):
    user = str(new_ulid())
    client.post(
        "/v1/creators/apply",
        json={"equipment": [], "region": "Kyoto", "id_doc_token": "id-3"},
        headers=_auth(user),
    )
    r = client.post(
        "/v1/creators/verify",
        json={"liveness_token": "lv-2", "geocheck": False},
        headers=_auth(user),
    )
    assert r.status_code == 422


def test_dashboard_aggregates_across_services(client):
    from worldview.db import get_session_factory

    creator = str(new_ulid())
    with get_session_factory()() as db:
        _seed_stream(db, "s-1", creator, status="live")
        _seed_stream(db, "s-2", creator, status="ended")
        _seed_tip(db, "t-1", creator, 500)
        _seed_tip(db, "t-2", creator, 700)
        _seed_payout(db, "p-1", creator, 1000, status="paid")
        _seed_payout(db, "p-2", creator, 250, status="pending")
        db.commit()

    client.post(
        "/v1/creators/apply",
        json={"equipment": [], "region": "NYC", "id_doc_token": "id-4"},
        headers=_auth(creator),
    )
    client.post("/v1/creators/verify", json={"liveness_token": "lv-3"}, headers=_auth(creator))

    r = client.get("/v1/creators/me/dashboard", headers=_auth(creator))
    assert r.status_code == 200
    body = r.json()
    assert body["total_streams"] == 2
    assert body["live_streams"] == 1
    assert body["total_tips_cents"] == 1200
    assert body["paid_payout_cents"] == 1000
    assert body["pending_payout_cents"] == 250


def test_streams_lists_creator_sessions(client):
    from worldview.db import get_session_factory

    creator = str(new_ulid())
    with get_session_factory()() as db:
        _seed_stream(db, "s-1", creator)
        _seed_stream(db, "s-2", creator)
        db.commit()

    client.post(
        "/v1/creators/apply",
        json={"equipment": [], "region": "Berlin", "id_doc_token": "id-5"},
        headers=_auth(creator),
    )
    r = client.get("/v1/creators/me/streams", headers=_auth(creator))
    assert r.status_code == 200
    assert {s["id"] for s in r.json()} == {"s-1", "s-2"}


def test_equipment_loan_request(client):
    user = str(new_ulid())
    client.post(
        "/v1/creators/apply",
        json={"equipment": [], "region": "Rome", "id_doc_token": "id-6"},
        headers=_auth(user),
    )
    r = client.post(
        "/v1/creators/me/equipment-loan", json={"equipment": "kandao-qoocam"}, headers=_auth(user)
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "requested"
    assert body["equipment"] == "kandao-qoocam"


def test_payouts_list(client):
    from datetime import UTC, datetime

    from worldview.db import get_session_factory

    creator = str(new_ulid())
    with get_session_factory()() as db:
        _seed_payout(
            db,
            "p-1",
            creator,
            500,
            status="paid",
            created_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
        _seed_payout(
            db,
            "p-2",
            creator,
            300,
            status="pending",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        db.commit()

    client.post(
        "/v1/creators/apply",
        json={"equipment": [], "region": "London", "id_doc_token": "id-7"},
        headers=_auth(creator),
    )
    r = client.get("/v1/creators/me/payouts", headers=_auth(creator))
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.json()[0]["status"] == "paid"


def test_private_tour_offer(client):
    user = str(new_ulid())
    client.post(
        "/v1/creators/apply",
        json={"equipment": [], "region": "Barcelona", "id_doc_token": "id-8"},
        headers=_auth(user),
    )
    r = client.post(
        "/v1/creators/me/private-tours",
        json={"title": "Gothic Quarter walk", "price_cents": 2400},
        headers=_auth(user),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Gothic Quarter walk"
    assert body["price_cents"] == 2400
    assert body["status"] == "draft"


def test_creator_endpoints_require_auth(client):
    r = client.get("/v1/creators/me/dashboard")
    assert r.status_code == 401
    r = client.post(
        "/v1/creators/apply",
        json={"equipment": [], "region": "x", "id_doc_token": "y"},
    )
    assert r.status_code == 401
