"""Catalog service API tests."""

import pytest
import worldview_catalog.main as main
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'catalog.db'}")
    from worldview.config import reset_settings

    reset_settings()
    from importlib import reload

    reload(main)
    with TestClient(main.app) as c:
        yield c


def _seed_tour(client, **kwargs):
    db = next(_session())
    from ulid import new as new_ulid
    from worldview_catalog.models import Tour

    defaults = {
        "id": str(new_ulid()),
        "title_en": "Eiffel Tower",
        "kind": "vod",
        "status": "published",
        "latitude": 48.8584,
        "longitude": 2.2945,
        "region_key": "eu-west-1",
        "is_free": True,
    }
    defaults.update(kwargs)
    tour = Tour(**defaults)
    db.add(tour)
    db.commit()


def _session():
    from worldview.db import get_session_factory

    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def test_list_published_tours(client):
    _seed_tour(client)
    r = client.get("/v1/tours")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["title_en"] == "Eiffel Tower"


def test_filter_by_kind(client):
    _seed_tour(client, kind="live", title_en="Tokyo Live")
    r = client.get("/v1/tours?kind=live")
    items = r.json()["items"]
    assert len(items) == 1 and items[0]["kind"] == "live"


def test_get_tour_404(client):
    assert client.get("/v1/tours/nonexistent").status_code == 404


def test_nearby_radius(client):
    _seed_tour(client)
    _seed_tour(client, title_en="Far Away", latitude=60.0, longitude=2.0)
    r = client.get("/v1/explore/nearby", params={"lat": 48.85, "lng": 2.29, "radius_km": 50})
    titles = [t["title_en"] for t in r.json()]
    assert "Eiffel Tower" in titles
    assert "Far Away" not in titles
