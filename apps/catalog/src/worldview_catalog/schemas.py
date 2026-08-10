"""Catalog request/response schemas."""

from pydantic import BaseModel, Field
from worldview.schemas import OrmModel


class TourOut(OrmModel):
    id: str
    title_en: str
    kind: str
    status: str
    latitude: float | None = None
    longitude: float | None = None
    price_cents: int
    is_free: bool
    premium: bool
    duration_sec: int | None = None
    language: str


class TourListOut(OrmModel):
    items: list[TourOut]
    next_cursor: str | None = None


class PoiOut(OrmModel):
    id: str
    tour_id: str
    name_en: str
    t_begin_sec: float
    t_end_sec: float | None
    look_dir: dict
    poi_type: str
    description_en: str | None


class HotspotOut(OrmModel):
    id: str
    poi_id: str
    kind: str
    payload: dict


class GeoFilter(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius_km: float = Field(default=25, gt=0, le=1000)


class TravelListIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_default: bool = False


class TravelListOut(OrmModel):
    id: str
    user_id: str
    name: str
    is_default: bool


class BookmarkIn(BaseModel):
    tour_id: str | None = None
    poi_id: str | None = None
    list_id: str | None = None
    note: str | None = Field(default=None, max_length=500)


class BookmarkOut(OrmModel):
    id: str
    user_id: str
    tour_id: str | None
    poi_id: str | None
    list_id: str | None
    note: str | None


class CaptureIn(BaseModel):
    kind: str = Field(default="vr_photo", pattern="^(vr_photo|memory_clip)$")
    t: float = Field(default=0.0, ge=0)
    url: str | None = None


class CaptureOut(OrmModel):
    id: str
    tour_id: str
    kind: str
    url: str
    t_begin: float
