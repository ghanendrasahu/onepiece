"""Streaming state machine.

States: PREPARING -> LIVE <-> PAUSED -> ENDED -> ARCHIVED

Transitions are validated in :func:`can_transition`; the session row carries a
``version`` column for optimistic concurrency (handled by the route layer).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class StreamStatus(StrEnum):
    PREPARING = "preparing"
    LIVE = "live"
    PAUSED = "paused"
    ENDED = "ended"
    ARCHIVED = "archived"


_TRANSITIONS: dict[StreamStatus, frozenset[StreamStatus]] = {
    StreamStatus.PREPARING: frozenset({StreamStatus.LIVE, StreamStatus.ENDED}),
    StreamStatus.LIVE: frozenset({StreamStatus.PAUSED, StreamStatus.ENDED}),
    StreamStatus.PAUSED: frozenset({StreamStatus.LIVE, StreamStatus.ENDED}),
    StreamStatus.ENDED: frozenset({StreamStatus.ARCHIVED}),
    StreamStatus.ARCHIVED: frozenset(),
}


class InvalidTransition(ValueError):
    pass


def can_transition(current: str, target: str) -> bool:
    try:
        return StreamStatus(target) in _TRANSITIONS[StreamStatus(current)]
    except (KeyError, ValueError):
        return False


@dataclass(frozen=True)
class Transition:
    current: str
    target: str

    def validate(self) -> None:
        if not can_transition(self.current, self.target):
            raise InvalidTransition(f"Invalid transition: {self.current} -> {self.target}")
