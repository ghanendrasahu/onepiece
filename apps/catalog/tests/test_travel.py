"""Catalog user-scoped routes: travel lists, bookmarks, captures."""

import pytest
import worldview_catalog.main as main
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


def _auth_headers():
    from ulid import new as new_ulid
    from worldview.auth import create_access_token

    return {"Authorization": f"Bearer {create_access_token(str(new_ulid()), scopes=['user'])}"}


def _seed_tour(client):
    from ulid import new as new_ulid
    from worldview.db import get_session_factory
    from worldview_catalog.models import Tour

    factory = get_session_factory()
    db = factory()
    try:
        tour = Tour(
            id=str(new_ulid()),
            title_en="Venezia",
            kind="vod",
            status="published",
            region_key="eu-west-1",
            is_free=True,
        )
        db.add(tour)
        db.commit()
        return tour.id
    finally:
        db.close()


def test_travel_list_lifecycle(client):
    headers = _auth_headers()
    created = client.post("/v1/travel-lists", json={"name": "Rome 2026"}, headers=headers)
    assert created.status_code == 201
    list_id = created.json()["id"]

    listed = client.get("/v1/travel-lists", headers=headers)
    assert [t["name"] for t in listed.json()] == ["Rome 2026"]
    assert [t["id"] for t in listed.json()] == [list_id]


def test_bookmark_and_delete(client):
    headers = _auth_headers()
    tour_id = _seed_tour(client)
    added = client.post(f"/v1/tours/{tour_id}/bookmark", json={"note": "must see"}, headers=headers)
    assert added.status_code == 201
    bookmark_id = added.json()["id"]
    assert added.json()["tour_id"] == tour_id

    listed = client.get("/v1/bookmarks", headers=headers)
    assert len(listed.json()) == 1

    assert client.delete(f"/v1/bookmarks/{bookmark_id}", headers=headers).status_code == 204
    assert client.get("/v1/bookmarks", headers=headers).json() == []


def test_bookmark_isolation_between_users(client):
    user_a = _auth_headers()
    user_b = _auth_headers()
    tour_id = _seed_tour(client)

    client.post(f"/v1/tours/{tour_id}/bookmark", json={}, headers=user_a)
    assert len(client.get("/v1/bookmarks", headers=user_a).json()) == 1
    assert client.get("/v1/bookmarks", headers=user_b).json() == []


def test_capture_creation(client):
    headers = _auth_headers()
    tour_id = _seed_tour(client)
    vr = client.post(
        f"/v1/tours/{tour_id}/capture", json={"kind": "vr_photo", "t": 12.5}, headers=headers
    )
    assert vr.status_code == 201
    assert vr.json()["kind"] == "vr_photo"
    assert vr.json()["t_begin"] == 12.5

    clip = client.post(
        f"/v1/tours/{tour_id}/capture", json={"kind": "memory_clip", "t": 3.0}, headers=headers
    )
    assert clip.status_code == 201
    assert clip.json()["kind"] == "memory_clip"

    listed = client.get("/v1/captures", headers=headers)
    assert len(listed.json()) == 2
    assert {c["kind"] for c in listed.json()} == {"vr_photo", "memory_clip"}
