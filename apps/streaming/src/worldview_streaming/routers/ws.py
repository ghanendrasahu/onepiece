"""Realtime WebSocket endpoints: shared-room chat, presence, tour events.

Protocol (docs/06-api-specification.md §7):
- Inbound frames ``{"type": "chat.send", body, reply_to?}`` become fanned-out
  ``chat.msg`` frames carrying an id, moderation flags, and a timestamp.
- ``{"type": "chat.reaction", msg_id, emoji}`` and leader-driven
  ``{"type": "watch.sync", t, playState}`` are validated and echoed verbatim.
- ``{"type": "room.kick", user_id}`` is only honoured for moderator scopes.
- Unauthenticated sockets are rejected with a 4401 close after an ``error``
  frame (safer than a bare close for mobile clients).
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ulid import new as new_ulid
from worldview.auth import decode_access_token
from worldview.config import get_settings

from ..moderation import RateLimiter, moderate
from ..realtime import RoomHub, get_room_hub

router = APIRouter(prefix="/v1", tags=["realtime"])

_MAX_BODY_LEN = 1000
_MODERATOR_SCOPE = "moderator"


def _claims_from_ws(websocket: WebSocket) -> dict[str, Any]:
    token = websocket.query_params.get("access_token") or websocket.query_params.get("token")
    if not token:
        raise PermissionError("missing access_token")
    return decode_access_token(token, get_settings())


async def _send_joined(
    websocket: WebSocket,
    hub: RoomHub,
    room: str,
    conn_id: str,
    claims: dict[str, Any],
) -> None:
    """Deliver history + current presence to the newly joined socket."""
    members = await hub.members(room)
    await websocket.send_json({"type": "presence.sync", "room": room, "members": members})
    messages = await hub.history(room)
    await websocket.send_json({"type": "chat.history", "room": room, "messages": messages})
    await websocket.send_json({"type": "conn.ready", "conn_id": conn_id, "user_id": claims["sub"]})


async def _broadcast_presence(hub: RoomHub, room: str) -> None:
    members = await hub.members(room)
    await hub.publish(room, {"type": "presence.sync", "room": room, "members": members})


async def _relay_loop(
    websocket: WebSocket,
    hub: RoomHub,
    room: str,
    conn_id: str,
    on_frame: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    """Race inbound client frames against hub fan-out and echo hub frames out."""
    recv = hub.next_frame(room, conn_id)
    inbound: asyncio.Task | None = None
    outbound: asyncio.Task | None = None

    while True:
        if inbound is None or inbound.done():
            inbound = asyncio.create_task(websocket.receive_text())
        if outbound is None or outbound.done():
            outbound = asyncio.create_task(recv())

        done, _ = await asyncio.wait({inbound, outbound}, return_when=asyncio.FIRST_COMPLETED)

        if inbound in done:
            try:
                data = inbound.result()
            except (ValueError, TypeError):
                data = None
            frame = json.loads(data) if data else {}
            await on_frame(frame)
        if outbound in done:
            try:
                payload = outbound.result()
            except (ValueError, TypeError):
                payload = None
            if payload is not None:
                try:
                    await websocket.send_json(json.loads(payload))
                except (ValueError, TypeError):
                    pass


@router.websocket("/tours/{tour_id}/chat")
async def tour_chat(websocket: WebSocket, tour_id: str) -> None:
    """Authenticated room chat for a tour's shared viewport."""
    await websocket.accept()
    try:
        claims = _claims_from_ws(websocket)
    except PermissionError:
        await websocket.send_json({"type": "error", "detail": "authentication required"})
        await websocket.close(code=4401)
        return

    hub = get_room_hub()
    conn_id = str(new_ulid())
    room = f"tour:{tour_id}"
    meta = {
        "conn_id": conn_id,
        "user_id": claims["sub"],
        "display_name": claims.get("display_name", "explorer"),
    }
    await hub.join(room, conn_id, meta)
    await _send_joined(websocket, hub, room, conn_id, claims)
    await _broadcast_presence(hub, room)
    limiter = RateLimiter()

    async def on_frame(frame: dict[str, Any]) -> None:
        ftype = frame.get("type")
        if ftype == "chat.send":
            await _on_chat_send(hub, room, conn_id, meta, frame, limiter)
        elif ftype == "chat.reaction":
            await _on_chat_reaction(hub, room, frame)
        elif ftype == "watch.sync":
            await _on_watch_sync(hub, room, frame)
        elif ftype == "room.kick":
            await _on_room_kick(hub, room, claims, frame)

    try:
        await _relay_loop(websocket, hub, room, conn_id, on_frame)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await hub.leave(room, conn_id)
        await _broadcast_presence(hub, room)


async def _on_chat_send(
    hub: RoomHub,
    room: str,
    conn_id: str,
    meta: dict[str, Any],
    frame: dict[str, Any],
    limiter: RateLimiter,
) -> None:
    body = str(frame.get("body", "") or "")[:_MAX_BODY_LEN]
    decision, mod_flags = moderate(body, limiter, conn_id)
    if decision in {"empty", "too_long"}:
        return
    if decision in {"blocked", "rate_limited"}:
        await hub.publish(
            room,
            {
                "type": "chat.rejected",
                "conn_id": conn_id,
                "reason": decision,
                "mod_flags": mod_flags,
            },
        )
        return
    event = {
        "type": "chat.msg",
        "msg_id": str(new_ulid()),
        "room": room,
        "conn_id": conn_id,
        "user_id": meta["user_id"],
        "display_name": meta["display_name"],
        "body": body,
        "reply_to": frame.get("reply_to"),
        "t": time.time(),
        "mod_flags": mod_flags,
    }
    await hub.publish(room, event)


async def _on_chat_reaction(hub: RoomHub, room: str, frame: dict[str, Any]) -> None:
    msg_id = frame.get("msg_id")
    emoji = frame.get("emoji")
    if not isinstance(msg_id, str) or not isinstance(emoji, str) or len(emoji) > 16:
        return
    await hub.publish(
        room, {"type": "chat.reaction", "room": room, "msg_id": msg_id, "emoji": emoji}
    )


async def _on_watch_sync(hub: RoomHub, room: str, frame: dict[str, Any]) -> None:
    t = frame.get("t")
    play_state = frame.get("playState")
    if not (isinstance(t, (int, float)) and isinstance(play_state, str)):
        return
    await hub.publish(
        room,
        {
            "type": "watch.sync",
            "room": room,
            "tour_id": frame.get("tour_id"),
            "t": float(t),
            "playState": play_state,
        },
    )


async def _on_room_kick(
    hub: RoomHub, room: str, claims: dict[str, Any], frame: dict[str, Any]
) -> None:
    scopes = claims.get("scopes") or []
    target = frame.get("user_id")
    if _MODERATOR_SCOPE in scopes and isinstance(target, str):
        await hub.publish(room, {"type": "room.kick", "room": room, "user_id": target})


@router.websocket("/streams/{stream_id}/events")
async def stream_events(websocket: WebSocket, stream_id: str) -> None:
    """Subscribe to tour/stream lifecycle events broadcast by the service."""
    await websocket.accept()
    try:
        _claims_from_ws(websocket)
    except PermissionError:
        await websocket.send_json({"type": "error", "detail": "authentication required"})
        await websocket.close(code=4401)
        return

    hub = get_room_hub()
    room = f"stream:{stream_id}"
    conn_id = str(new_ulid())
    await hub.join(room, conn_id, {"conn_id": conn_id, "user_id": "subscriber"})
    events = await hub.tour_events(stream_id)
    await websocket.send_json({"type": "stream.snapshot", "stream_id": stream_id, "events": events})

    async def on_frame(frame: dict[str, Any]) -> None:
        return None

    try:
        await _relay_loop(websocket, hub, room, conn_id, on_frame)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await hub.leave(room, conn_id)
