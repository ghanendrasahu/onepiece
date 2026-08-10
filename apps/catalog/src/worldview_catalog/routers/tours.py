"""Catalog routes: browse, detail, POIs, hotspots, categories."""

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


@router.get("/tours", response_model=TourListOut)
def list_tours(
    q: str | None = None,
    kind: str | None = None,
    category: str | None = None,
    cursor: int = 0,
    limit: int = Query(default=25, le=100),
    db: Session = Depends(get_db),
) -> TourListOut:
    stmt = select(Tour).where(Tour.status == "published")
    if kind:
        stmt = stmt.where(Tour.kind == kind)
    if category:
        stmt = stmt.join(TourCategory).where(TourCategory.category == category)
    if q:
        stmt = stmt.where(func.lower(Tour.title_en).contains(q.lower()))
    stmt = stmt.order_by(Tour.created_at.desc()).offset(cursor).limit(limit + 1)
    rows = list(db.execute(stmt).scalars())
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = str(cursor + limit) if has_more else None
    return TourListOut(items=[_tour_out(db, t) for t in rows], next_cursor=next_cursor)


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
def list_pois(tour_id: str, t: float = 0.0, db: Session = Depends(get_db)) -> list[Poi]:
    rows = db.execute(select(Poi).where(Poi.tour_id == tour_id, Poi.t_begin_sec <= t)).scalars()
    return list(rows)


@router.get("/pois/{poi_id}", response_model=PoiOut)
def get_poi(poi_id: str, db: Session = Depends(get_db)) -> Poi:
    poi = db.get(Poi, poi_id)
    if poi is None:
        raise HTTPException(status_code=404, detail="POI not found")
    return poi


@router.get("/tours/{tour_id}/hotspots", response_model=list[HotspotOut])
def list_hotspots(tour_id: str, db: Session = Depends(get_db)) -> list[Hotspot]:
    stmt = select(Hotspot).join(Poi, Poi.id == Hotspot.poi_id).where(Poi.tour_id == tour_id)
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
    import math

    lat, lng, radius = filters.lat, filters.lng, filters.radius_km
    rows = db.execute(select(Tour).where(Tour.status == "published")).scalars()
    matches = []
    for tour in rows:
        if tour.latitude is None or tour.longitude is None:
            continue
        t_lat = float(tour.latitude)
        t_lng = float(tour.longitude)
        dlat = math.radians(t_lat - lat)
        dlng = math.radians(t_lng - lng)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat)) * math.cos(math.radians(t_lat)) * math.sin(dlng / 2) ** 2
        )
        dist = 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        if dist <= radius:
            matches.append(_tour_out(db, tour))
    return matches
