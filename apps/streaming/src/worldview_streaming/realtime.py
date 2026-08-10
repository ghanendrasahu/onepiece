"""WebSocket chat, presence, and tour-event fan-out for shared VR rooms.

The room hub is pluggable. :class:`MemoryRoomHub` (the default) keeps presence,
recent chat history, and a small tour-event log in process memory and fans each
message out to every socket that has joined the room. When ``REDIS_URL`` is set,
:func:`build_room_hub` returns a :class:`RedisRoomHub` that mirrors the same
state model locally and additionally publishes messages onto Redis channels so
multiple service instances stay in sync.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Protocol

_HISTORY_LIMIT = 100

_logger = logging.getLogger("worldview_streaming.realtime")


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


class RoomHub(Protocol):
    """Fan-out + presence storage surface for a realtime room."""

    async def join(self, room: str, conn_id: str, meta: dict[str, Any]) -> None: ...

    async def leave(self, room: str, conn_id: str) -> None: ...

    async def members(self, room: str) -> list[dict[str, Any]]: ...

    async def history(self, room: str) -> list[dict[str, Any]]: ...

    def next_frame(self, room: str, conn_id: str) -> Callable[[], Any]: ...

    async def publish(self, room: str, event: dict[str, Any]) -> None: ...

    async def publish_tour_event(self, tour_id: str, event: dict[str, Any]) -> None: ...

    async def tour_events(self, tour_id: str) -> list[dict[str, Any]]: ...


class MemoryRoomHub:
    """Process-local room hub. Single instance / dev test-compatible default."""

    def __init__(self, history_limit: int = _HISTORY_LIMIT) -> None:
        self._members: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        self._queues: dict[str, dict[str, asyncio.Queue]] = defaultdict(dict)
        self._history: dict[str, deque] = defaultdict(lambda: deque(maxlen=history_limit))
        self._tour_events: dict[str, deque] = defaultdict(lambda: deque(maxlen=history_limit))

    def _queue(self, room: str, conn_id: str) -> asyncio.Queue:
        return self._queues[room].setdefault(conn_id, asyncio.Queue())

    async def join(self, room: str, conn_id: str, meta: dict[str, Any]) -> None:
        self._members[room][conn_id] = meta
        self._queue(room, conn_id)

    async def leave(self, room: str, conn_id: str) -> None:
        self._members[room].pop(conn_id, None)
        self._queues[room].pop(conn_id, None)

    async def members(self, room: str) -> list[dict[str, Any]]:
        return list(self._members[room].values())

    async def history(self, room: str) -> list[dict[str, Any]]:
        return list(self._history[room])

    def next_frame(self, room: str, conn_id: str) -> Callable[[], Any]:
        """Return a ``socket.recv``-style awaitable yielding the next JSON frame."""

        async def _recv() -> str | None:
            try:
                return await self._queue(room, conn_id).get()
            except asyncio.CancelledError:
                return None

        return _recv

    async def publish(self, room: str, event: dict[str, Any]) -> None:
        if event.get("type") == "chat.msg":
            self._history[room].append(event)
        payload = json.dumps(event, default=str, ensure_ascii=False)
        for queue in list(self._queues[room].values()):
            queue.put_nowait(payload)

    async def publish_tour_event(self, tour_id: str, event: dict[str, Any]) -> None:
        self._tour_events[tour_id].append(event)

    async def tour_events(self, tour_id: str) -> list[dict[str, Any]]:
        return list(self._tour_events[tour_id])


class RedisRoomHub(MemoryRoomHub):
    """Memory-first hub whose chat frames additionally travel over Redis.

    Local presence/history stay in process; ``publish`` also pushes the frame
    onto a per-room Redis channel. A per-room subscriber task delivers frames
    published by other instances into this process's queues, keeping large
    fan-out consistent. Imports ``redis`` lazily so dev without Redis works.
    """

    def __init__(self, redis_url: str, history_limit: int = _HISTORY_LIMIT) -> None:
        super().__init__(history_limit)
        import redis

        self._redis: Any = redis.from_url(
            redis_url, decode_responses=True, socket_connect_timeout=2
        )
        self._subscribers: dict[str, asyncio.Task] = {}
        self._closed = False

    def _channel(self, room: str) -> str:
        return f"room:{room}"

    async def publish(self, room: str, event: dict[str, Any]) -> None:
        await super().publish(room, event)
        try:
            self._redis.publish(self._channel(room), json.dumps(event, default=str))
        except Exception as exc:  # redis unavailable: local fan-out still succeeds
            _logger.warning("redis publish failed", extra={"error": str(exc)})

    async def join(self, room: str, conn_id: str, meta: dict[str, Any]) -> None:
        await super().join(room, conn_id, meta)
        task = self._subscribers.get(room)
        if task is None or task.done():
            self._subscribers[room] = asyncio.create_task(self._bridge_room(room))

    async def _bridge_room(self, room: str) -> None:
        """Relay cross-instance frames into this process's local queues."""
        from redis.exceptions import RedisError

        try:
            pubsub = self._redis.pubsub()
            pubsub.subscribe(self._channel(room))
            while not self._closed:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    try:
                        event = json.loads(message["data"])
                    except (TypeError, ValueError):
                        continue
                    if not self._has_local(event.get("conn_id")):
                        if event.get("type") == "chat.msg":
                            self._history[room].append(event)
                        payload = json.dumps(event, default=str, ensure_ascii=False)
                        for queue in list(self._queues[room].values()):
                            queue.put_nowait(payload)
            pubsub.close()
        except (RedisError, OSError, asyncio.CancelledError):
            return

    def _has_local(self, conn_id: Any) -> bool:
        if conn_id is None:
            return False
        return any(conn_id in members for members in self._members.values())

    async def close(self) -> None:
        self._closed = True
        for task in self._subscribers.values():
            task.cancel()


def build_room_hub(redis_url: str | None) -> RoomHub:
    """Return a Redis-backed hub when a URL is configured, else an in-memory one."""
    if redis_url:
        return RedisRoomHub(redis_url)
    return MemoryRoomHub()


@lru_cache(maxsize=1)
def get_room_hub(redis_url: str | None = None) -> RoomHub:
    """Return the process-wide hub shared by every WebSocket handler."""
    from worldview.config import get_settings

    return build_room_hub(redis_url if redis_url is not None else get_settings().redis_url)
