"""Seed the catalog with demo tours, POIs, and hotspots.

Idempotent: skips seeding when the catalog already has tours. Used by local dev
(``make seed``), CI, and the smoke test so the AI guide grounds answers in real
catalog content instead of its bundled seed.
"""

from __future__ import annotations

import argparse
import os

from sqlalchemy import create_engine, select
from worldview.db import Base, get_session_factory
from worldview_catalog.models import Hotspot, Poi, Tour

_TOURS = [
    {
        "id": "tour-tokyo",
        "title_en": "Tokyo Night Walk",
        "kind": "ai_guided",
        "status": "published",
        "latitude": 35.6586,
        "longitude": 139.7454,
        "region_key": "ap-southeast-1",
        "is_free": True,
        "language": "en",
        "duration_sec": 3600,
    },
    {
        "id": "tour-paris",
        "title_en": "Paris Day Stroll",
        "kind": "ai_guided",
        "status": "published",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "region_key": "eu-west-1",
        "is_free": True,
        "language": "en",
        "duration_sec": 3000,
    },
]

_POIS = [
    {
        "id": "poi-tokyo-tower",
        "tour_id": "tour-tokyo",
        "name_en": "Tokyo Tower",
        "t_begin_sec": 10.0,
        "t_end_sec": 180.0,
        "look_dir": {"yaw": 0.0, "pitch": 0.0},
        "poi_type": "landmark",
        "description_en": (
            "Tokyo Tower is a communications and observation tower in Shiba Park, built in 1958. "
            "Standing 332.9 metres tall, it was inspired by the Eiffel Tower."
        ),
    },
    {
        "id": "poi-shibuya-crossing",
        "tour_id": "tour-tokyo",
        "name_en": "Shibuya Crossing",
        "t_begin_sec": 0.0,
        "t_end_sec": 120.0,
        "look_dir": {"yaw": 90.0, "pitch": 0.0},
        "poi_type": "street",
        "description_en": (
            "Shibuya Crossing is one of the world's busiest pedestrian scrambles, seeing up to "
            "3,000 people cross at once during peak times."
        ),
    },
    {
        "id": "poi-skytree",
        "tour_id": "tour-tokyo",
        "name_en": "Tokyo Skytree",
        "t_begin_sec": 200.0,
        "t_end_sec": 400.0,
        "look_dir": {"yaw": 180.0, "pitch": 0.0},
        "poi_type": "landmark",
        "description_en": (
            "Tokyo Skytree is the world's tallest tower at 634 metres, home to two observation "
            "decks overlooking the Kanto plain."
        ),
    },
    {
        "id": "poi-eiffel",
        "tour_id": "tour-paris",
        "name_en": "Eiffel Tower",
        "t_begin_sec": 0.0,
        "t_end_sec": None,
        "look_dir": {"yaw": 0.0, "pitch": 0.0},
        "poi_type": "landmark",
        "description_en": (
            "The Eiffel Tower was completed in 1889 for the World's Fair, standing 330 metres "
            "tall. It was the world's tallest structure until 1930."
        ),
    },
]

_HOTSPOTS = [
    {"id": "hs-skydeck", "poi_id": "poi-skytree", "kind": "info", "payload": {"label": "Sky Deck"}},
    {"id": "hs-crossing-view", "poi_id": "poi-shibuya-crossing", "kind": "photo", "payload": {}},
    {"id": "hs-eiffel-sparkle", "poi_id": "poi-eiffel", "kind": "info", "payload": {}},
]


def seed(database_url: str) -> str:
    """Insert demo data. Returns ``"seeded"`` or ``"skipped"`` if already populated."""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    with get_session_factory(database_url)() as db:
        if db.execute(select(Tour).limit(1)).first() is not None:
            return "skipped (catalog already populated)"

        tours = [Tour(**row) for row in _TOURS]
        db.add_all(tours)
        db.add_all(Poi(**row) for row in _POIS)
        db.add_all(Hotspot(**row) for row in _HOTSPOTS)
        db.commit()
    return f"seeded {len(_TOURS)} tours, {len(_POIS)} POIs, {len(_HOTSPOTS)} hotspots"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url", default=os.environ.get("DATABASE_URL", "sqlite:///./data/worldview.db")
    )
    args = parser.parse_args()
    print(seed(args.url))


if __name__ == "__main__":
    main()
