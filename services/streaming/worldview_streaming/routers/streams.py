"""Streaming routes: lifecycle CRUD + transitions."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ulid import new as new_ulid
from worldview.auth import get_current_user
from worldview.db import get_db

from ..models import StreamSession
from ..schemas import CreateStreamIn, StreamOut
from ..state_machine import InvalidTransition, Transition

router = APIRouter(prefix="/v1/streams", tags=["streams"])

_STREAM_KEY_ENDPOINT = "srt://ingest.worldview.vr:5001"


@router.post("", response_model=StreamOut, status_code=status.HTTP_201_CREATED)
def create_stream(
    payload: CreateStreamIn,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamSession:
    session_row = StreamSession(
        id=str(new_ulid()),
        tour_id=payload.tour_id,
        creator_id=claims["sub"],
        quality_ladder=payload.quality_ladder,
        spatial_audio=payload.spatial_audio,
        ingest_endpoint=_STREAM_KEY_ENDPOINT,
    )
    db.add(session_row)
    db.flush()
    return session_row


@router.get("/live", response_model=list[StreamOut])
def list_live(db: Session = Depends(get_db)) -> list[StreamSession]:
    rows = db.execute(select(StreamSession).where(StreamSession.status == "live")).scalars()
    return list(rows)


@router.get("/{stream_id}", response_model=StreamOut)
def get_stream(stream_id: str, db: Session = Depends(get_db)) -> StreamSession:
    return _get_or_404(stream_id, db)


@router.post("/{stream_id}/start", response_model=StreamOut)
def start_stream(
    stream_id: str,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamSession:
    session_row = _get_or_404(stream_id, db)
    _authorize_creator(session_row, claims)
    _apply(db, session_row, "live", started_at=datetime.now(UTC))
    return session_row


@router.post("/{stream_id}/pause", response_model=StreamOut)
def pause_stream(
    stream_id: str,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamSession:
    session_row = _get_or_404(stream_id, db)
    _authorize_creator(session_row, claims)
    _apply(db, session_row, "paused")
    return session_row


@router.post("/{stream_id}/resume", response_model=StreamOut)
def resume_stream(
    stream_id: str,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamSession:
    session_row = _get_or_404(stream_id, db)
    _authorize_creator(session_row, claims)
    _apply(db, session_row, "live")
    return session_row


@router.post("/{stream_id}/end", response_model=StreamOut)
def end_stream(
    stream_id: str,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamSession:
    session_row = _get_or_404(stream_id, db)
    _authorize_creator(session_row, claims)
    _apply(db, session_row, "ended", ended_at=datetime.now(UTC))
    return session_row


def _get_or_404(stream_id: str, db: Session) -> StreamSession:
    session_row = db.get(StreamSession, stream_id)
    if session_row is None:
        raise HTTPException(status_code=404, detail="Stream not found")
    return session_row


def _authorize_creator(session_row: StreamSession, claims: dict) -> None:
    if session_row.creator_id != claims["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the stream creator")


def _apply(db: Session, session_row: StreamSession, target: str, **fields) -> None:
    try:
        Transition(session_row.status, target).validate()
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    for key, value in fields.items():
        setattr(session_row, key, value)
    session_row.status = target
    session_row.version += 1
