"""User-scoped catalog routes: travel lists, bookmarks, captures."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ulid import new as new_ulid
from worldview.auth import get_current_user
from worldview.db import get_db

from ..models import Bookmark, Capture, TravelList
from ..schemas import (
    BookmarkIn,
    BookmarkOut,
    CaptureIn,
    CaptureOut,
    TravelListIn,
    TravelListOut,
)

router = APIRouter(prefix="/v1", tags=["catalog/user"])


def _get_or_404(model, obj_id: str, db: Session):
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Not found")
    return obj


@router.get("/travel-lists", response_model=list[TravelListOut])
def list_travel_lists(
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TravelList]:
    rows = db.execute(select(TravelList).where(TravelList.user_id == claims["sub"])).scalars()
    return list(rows)


@router.post("/travel-lists", response_model=TravelListOut, status_code=status.HTTP_201_CREATED)
def create_travel_list(
    payload: TravelListIn,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TravelList:
    row = TravelList(
        id=str(new_ulid()),
        user_id=claims["sub"],
        name=payload.name,
        is_default=payload.is_default,
    )
    db.add(row)
    db.flush()
    return row


@router.get("/bookmarks", response_model=list[BookmarkOut])
def list_bookmarks(
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Bookmark]:
    rows = db.execute(select(Bookmark).where(Bookmark.user_id == claims["sub"])).scalars()
    return list(rows)


@router.post("/tours/{tour_id}/bookmark", response_model=BookmarkOut, status_code=201)
def add_bookmark(
    tour_id: str,
    payload: BookmarkIn,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Bookmark:
    row = Bookmark(
        id=str(new_ulid()),
        user_id=claims["sub"],
        tour_id=tour_id,
        poi_id=payload.poi_id,
        list_id=payload.list_id,
        note=payload.note,
    )
    db.add(row)
    db.flush()
    return row


@router.delete("/bookmarks/{bookmark_id}", status_code=204)
def delete_bookmark(
    bookmark_id: str,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    bookmark = db.get(Bookmark, bookmark_id)
    if bookmark is None or bookmark.user_id != claims["sub"]:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    db.delete(bookmark)


@router.post("/tours/{tour_id}/capture", response_model=CaptureOut, status_code=201)
def create_capture(
    tour_id: str,
    payload: CaptureIn,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Capture:
    capture = Capture(
        id=str(new_ulid()),
        user_id=claims["sub"],
        tour_id=tour_id,
        kind=payload.kind,
        url=payload.url or f"/v1/captures/{str(new_ulid())}/signed",
        t_begin=payload.t,
        t_end=payload.t + 30 if payload.kind == "memory_clip" else None,
    )
    db.add(capture)
    db.flush()
    return capture


@router.get("/captures", response_model=list[CaptureOut])
def list_captures(
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Capture]:
    rows = db.execute(select(Capture).where(Capture.user_id == claims["sub"])).scalars()
    return list(rows)
