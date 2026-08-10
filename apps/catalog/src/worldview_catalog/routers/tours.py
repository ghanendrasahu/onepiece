"""Catalog routes: browse, detail, POIs, hotspots, categories."""

import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from worldview.db import get_db

from ..models import Hotspot, Poi, Tour, TourCategory
from ..schemas import (
    CategoriesOut,
    GeoFilter,
    HotspotOut,
    PoiOut,
    TourListOut,
    TourOut,
)

router = APIRouter(prefix="/v1", tags=["catalog"])

_CATEGORIES = ("landmark", "city", "nature", "festival", "culture", "concert")


def _tour_categories(db: Session, tour_id: str) -> list[str]:
    rows = db.execute(select(TourCategory).where(TourCategory.tour_id == tour_id)).scalars()
    return [row.category for row in rows]


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.get("/tours", response_model=TourListOut)
def list_tours(
    q: str | None = None,
    kind: str | None = None,
    category: str | None = None,
    status: str = Query(default="published"),
    geo: str | None = Query(default=None, description="lat,lng,radius_km (e.g. 35.68,139.76,25)"),
    sort: str = Query(default="new", pattern="^(new|trending|price_asc|price_desc)$"),
    cursor: int = 0,
    limit: int = Query(default=25, le=100),
    db: Session = Depends(get_db),
) -> TourListOut:
    stmt = select(Tour).where(Tour.status == status)
    if kind:
        stmt = stmt.where(Tour.kind == kind)
    if category:
        stmt = stmt.join(TourCategory).where(TourCategory.category == category)
    if q:
        stmt = stmt.where(func.lower(Tour.title_en).contains(q.lower()))
    rows = list(db.execute(stmt).scalars())

    latitude = lng = radius = None
    if geo:
        try:
            latitude, lng, radius = (float(part) for part in geo.split(","))
        except ValueError:
            raise HTTPException(status_code=422, detail="geo must be lat,lng,radius_km") from None

    if latitude is not None and lng is not None and radius is not None:
        rows = [
            t
            for t in rows
            if t.longitude is not None
            and t.latitude is not None
            and _haversine_km(latitude, lng, float(t.latitude), float(t.longitude)) <= radius
        ]

    if sort == "trending":
        rows = sorted(rows, key=lambda t: t.duration_sec or 0, reverse=True)
    elif sort == "price_asc":
        rows.sort(key=lambda t: t.price_cents)
    elif sort == "price_desc":
        rows.sort(key=lambda t: t.price_cents, reverse=True)
    else:
        rows.sort(key=lambda t: t.id, reverse=True)

    has_more = len(rows) > cursor + limit
    page = rows[cursor : cursor + limit]
    next_cursor = str(cursor + limit) if has_more else None
    return TourListOut(items=[_tour_out(db, t) for t in page], next_cursor=next_cursor)


def _tour_out(db: Session, tour: Tour) -> TourOut:
    out = TourOut.model_validate(tour)
    out.categories = _tour_categories(db, tour.id)
    return out


@router.get("/tours/{tour_id}", response_model=TourOut)
def get_tour(tour_id: str, db: Session = Depends(get_db)) -> TourOut:
    tour = db.get(Tour, tour_id)
    if tour is None:
        raise HTTPException(status_code=404, detail="Tour not found")
    return _tour_out(db, tour)


@router.get("/tours/{tour_id}/pois", response_model=list[PoiOut])
def list_pois(
    tour_id: str,
    t: float = 0.0,
    look_dir: str | None = Query(default=None, description="yaw,pitch"),
    db: Session = Depends(get_db),
) -> list[Poi]:
    """POIs visible at timeline ``t``; ``look_dir`` is accepted for parity."""
    rows = db.execute(select(Poi).where(Poi.tour_id == tour_id, Poi.t_begin_sec <= t)).scalars()
    return list(rows)


@router.get("/pois/{poi_id}", response_model=PoiOut)
def get_poi(poi_id: str, db: Session = Depends(get_db)) -> Poi:
    poi = db.get(Poi, poi_id)
    if poi is None:
        raise HTTPException(status_code=404, detail="POI not found")
    return poi


@router.get("/tours/{tour_id}/hotspots", response_model=list[HotspotOut])
def list_hotspots(
    tour_id: str,
    t: float = 0.0,
    db: Session = Depends(get_db),
) -> list[Hotspot]:
    stmt = select(Hotspot).join(Poi, Poi.id == Hotspot.poi_id).where(Poi.tour_id == tour_id)
    if t:
        stmt = stmt.where(Poi.t_begin_sec <= t)
    return list(db.execute(stmt).scalars())


@router.get("/categories", response_model=CategoriesOut)
def categories(db: Session = Depends(get_db)) -> CategoriesOut:
    seeded = list(_CATEGORIES)
    used = db.execute(
        select(func.distinct(TourCategory.category)).order_by(TourCategory.category)
    ).scalars()
    merged = list(dict.fromkeys(list(used) + seeded))
    return CategoriesOut(categories=merged)


@router.get("/explore/nearby", response_model=list[TourOut])
def tours_nearby(
    filters: Annotated[GeoFilter, Query()],
    db: Session = Depends(get_db),
) -> list[TourOut]:
    lat, lng, radius = filters.lat, filters.lng, filters.radius_km
    rows = db.execute(select(Tour).where(Tour.status == "published")).scalars()
    return [
        _tour_out(db, tour)
        for tour in rows
        if tour.latitude is not None
        and tour.longitude is not None
        and _haversine_km(lat, lng, float(tour.latitude), float(tour.longitude)) <= radius
    ]
