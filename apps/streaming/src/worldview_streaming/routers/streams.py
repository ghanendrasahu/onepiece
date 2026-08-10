"""Streaming routes: lifecycle CRUD + transitions."""

import asyncio
from datetime import UTC, datetime

import worldview_payments.models as _payments_models  # noqa: F401  (register tables)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ulid import new as new_ulid
from worldview.auth import get_current_user
from worldview.db import get_db

from ..models import StreamSession
from ..realtime import utc_iso
from ..schemas import (
    CreateStreamIn,
    ManifestOut,
    StreamOut,
    StreamReportAccepted,
    StreamReportIn,
    StreamStatsOut,
    TipAccepted,
    TipIn,
)
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


@router.get("/{stream_id}/manifest", response_model=ManifestOut)
def get_manifest(stream_id: str, db: Session = Depends(get_db)) -> ManifestOut:
    from ..manifest import build_manifest

    session_row = _get_or_404(stream_id, db)
    if session_row.status not in {"live", "paused"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stream is {session_row.status}; no manifest available",
        )
    return build_manifest(session_row)


@router.get("/{stream_id}", response_model=StreamOut)
def get_stream(stream_id: str, db: Session = Depends(get_db)) -> StreamSession:
    return _get_or_404(stream_id, db)


@router.post("/{stream_id}/report", response_model=StreamReportAccepted)
def report_stream(
    stream_id: str,
    payload: StreamReportIn,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamReportAccepted:
    """Forward a viewer report about this stream to the moderation service."""
    _get_or_404(stream_id, db)
    from ..moderation_client import submit_report

    report_id = submit_report(
        stream_id=stream_id,
        reporter_id=claims["sub"],
        reason=payload.reason,
        context=payload.context,
    )
    if report_id is None:
        raise HTTPException(status_code=503, detail="Moderation service unavailable")
    return StreamReportAccepted(report_id=report_id)


@router.post("/{stream_id}/tip", response_model=TipAccepted, status_code=201)
def tip_stream(
    stream_id: str,
    payload: TipIn,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TipAccepted:
    """Creator tip alias; forwards money to the payments service (docs/06 §5)."""
    _get_or_404(stream_id, db)
    from ..payments_client import submit_tip

    body = submit_tip(
        stream_id=stream_id,
        user_id=claims["sub"],
        cents=payload.cents,
        message=payload.message,
        idempotency_key=payload.idempotency_key,
    )
    if body is None:
        raise HTTPException(status_code=503, detail="Payments service unavailable")
    return TipAccepted(tip_id=body["id"])


@router.get("/{stream_id}/stats", response_model=StreamStatsOut)
def stream_stats(
    stream_id: str,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamStatsOut:
    """Creator stats: live viewers + cumulative tips (docs/06 §5)."""
    session_row = _get_or_404(stream_id, db)
    if session_row.creator_id != claims["sub"]:
        raise HTTPException(status_code=403, detail="Not the stream creator")

    from sqlalchemy import func
    from worldview_payments.models import Tip

    room = f"stream:{stream_id}"
    viewers = asyncio.run(_count_viewers(room))

    tips_cents = db.scalar(
        select(func.coalesce(func.sum(Tip.cents), 0)).where(Tip.stream_id == stream_id)
    )
    return StreamStatsOut(id=stream_id, viewers=viewers, tips_cents=tips_cents or 0)


async def _count_viewers(room: str) -> int:
    from ..realtime import get_room_hub

    hub = get_room_hub()
    return len(await hub.members(room))


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
    _publish_tour_event(session_row)


def _publish_tour_event(session_row: StreamSession) -> None:
    """Emit a lifecycle event to WS subscribers on /v1/streams/{id}/events."""
    from ..realtime import get_room_hub

    hub = get_room_hub()
    event = {
        "type": "stream.state",
        "stream_id": session_row.id,
        "tour_id": session_row.tour_id,
        "status": session_row.status,
        "version": session_row.version,
        "ts": utc_iso(),
    }
    room = f"stream:{session_row.id}"
    loop = _current_loop()
    if loop is None:
        asyncio.run(_emit(hub, room, session_row.id, event))
    else:
        loop.create_task(_emit(hub, room, session_row.id, event))


def _current_loop():
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


async def _emit(hub, room: str, stream_id: str, event: dict) -> None:
    members = await hub.members(room)
    event["viewers"] = len(members)
    await hub.publish_tour_event(stream_id, event)
    await hub.publish(room, event)
