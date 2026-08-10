"""Catalog service API tests."""

import pytest
import worldview_catalog.main as main
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from worldview.testing import test_database_url, truncate_all

    url = test_database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", url)
    from worldview.config import reset_settings

    reset_settings()
    from importlib import reload

    reload(main)
    with TestClient(main.app) as c:
        truncate_all(url)
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


def test_get_tour_categories_default_empty(client):
    _seed_tour(client)
    r = client.get("/v1/tours")
    assert r.json()["items"][0]["categories"] == []


def test_filter_by_category(client):
    from ulid import new as new_ulid
    from worldview_catalog.models import Tour, TourCategory

    tour = Tour(
        **{
            "id": str(new_ulid()),
            "title_en": "Tokyo Night Walk",
            "kind": "ai_guided",
            "status": "published",
            "latitude": 35.6586,
            "longitude": 139.7454,
            "region_key": "ap-southeast-1",
            "is_free": True,
        }
    )
    sess = next(_session())
    sess.add(tour)
    sess.add(TourCategory(tour_id=tour.id, category="city"))
    sess.add(TourCategory(tour_id=tour.id, category="culture"))
    sess.commit()

    r = client.get("/v1/tours?category=city")
    titles = [t["title_en"] for t in r.json()["items"]]
    assert titles == ["Tokyo Night Walk"]
    assert r.json()["items"][0]["categories"] == ["city", "culture"]


def test_list_categories(client):
    _seed_tour(client)
    r = client.get("/v1/categories")
    assert r.status_code == 200
    assert isinstance(r.json()["categories"], list)
    assert "landmark" in r.json()["categories"]


def test_get_poi(client):
    from ulid import new as new_ulid
    from worldview_catalog.models import Poi, Tour

    tour = Tour(
        **{
            "id": str(new_ulid()),
            "title_en": "Tour Two",
            "kind": "vod",
            "status": "published",
            "latitude": 48.85,
            "longitude": 2.29,
            "region_key": "eu-west-1",
            "is_free": True,
        }
    )
    sess = next(_session())
    sess.add(tour)
    sess.flush()
    poi = Poi(
        id=str(new_ulid()),
        tour_id=tour.id,
        name_en="Shibuya Crossing",
        t_begin_sec=0.0,
        t_end_sec=120.0,
        look_dir={"yaw": 90.0, "pitch": 0.0},
        poi_type="street",
    )
    sess.add(poi)
    sess.commit()
    r = client.get(f"/v1/pois/{poi.id}")
    assert r.status_code == 200
    assert r.json()["name_en"] == "Shibuya Crossing"


def test_get_poi_404(client):
    assert client.get("/v1/pois/nonexistent").status_code == 404


def test_nearby_radius(client):
    _seed_tour(client)
    _seed_tour(client, title_en="Far Away", latitude=60.0, longitude=2.0)
    r = client.get("/v1/explore/nearby", params={"lat": 48.85, "lng": 2.29, "radius_km": 50})
    titles = [t["title_en"] for t in r.json()]
    assert "Eiffel Tower" in titles
    assert "Far Away" not in titles


def test_tours_geo_filter(client):
    _seed_tour(client)
    _seed_tour(client, title_en="Far Away", latitude=60.0, longitude=2.0)
    r = client.get("/v1/tours", params={"geo": "48.85,2.29,50"})
    titles = [t["title_en"] for t in r.json()["items"]]
    assert "Eiffel Tower" in titles
    assert "Far Away" not in titles


def test_tours_geo_invalid(client):
    r = client.get("/v1/tours", params={"geo": "not-a-valid-triple"})
    assert r.status_code == 422


def test_tours_sort_by_price(client):
    _seed_tour(client, title_en="Cheap", price_cents=500, is_free=False)
    _seed_tour(client, title_en="Pricy", price_cents=9900, is_free=False)
    r = client.get("/v1/tours", params={"sort": "price_asc"})
    titles = [t["title_en"] for t in r.json()["items"]]
    assert titles == ["Cheap", "Pricy"]


def test_hotspots_filtered_by_t(client):
    from ulid import new as new_ulid
    from worldview_catalog.models import Hotspot, Poi, Tour

    tour = Tour(
        **{
            "id": str(new_ulid()),
            "title_en": "T Tour",
            "kind": "vod",
            "status": "published",
            "latitude": 48.85,
            "longitude": 2.29,
            "region_key": "eu-west-1",
            "is_free": True,
        }
    )
    sess = next(_session())
    sess.add(tour)
    sess.flush()
    poi_late = Poi(
        id=str(new_ulid()),
        tour_id=tour.id,
        name_en="Late POI",
        t_begin_sec=120.0,
        look_dir={"yaw": 0.0, "pitch": 0.0},
        poi_type="street",
    )
    sess.add(poi_late)
    sess.commit()
    sess.add(Hotspot(id=str(new_ulid()), poi_id=poi_late.id, kind="audio", payload={}))
    sess.commit()

    assert client.get(f"/v1/tours/{tour.id}/hotspots?t=50").json() == []
    assert len(client.get(f"/v1/tours/{tour.id}/hotspots?t=200").json()) == 1
