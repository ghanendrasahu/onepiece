"""Real-time chat moderation rules (FR-9.1).

T0 ships a self-contained rules engine that runs on every chat frame before it
is fanned out: a profanity blocklist, phishing/contact-harvesting heuristics, and
duplicate-flood protection. Messages that trip a hard rule are withheld (and
rejected back to the sender); borderline ones are flagged for human review and
still delivered with a ``mod_flags`` hint. A cloud classifier slot is left as a
``MODERATION_CLASSIFIER_URL`` hook for the T0/T1 road.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque

_BLOCKED_WORDS: frozenset[str] = frozenset(
    {
        "kurwa",
        "puta",
        "putain",
        "coño",
        "connard",
        "hurensohn",
        "아이씨",
        "ばか",
        "คำหยาบ",
    }
)

_CONTACT_RE = re.compile(
    (
        r"(?:[+\d][\d .()\-]{6,}\d|[\w.+-]+@[\w-]+\.[\w.]+|"
        r"(?:t|tg|telegram|whatsapp)[\s.]*(?:me/|\.com/|/)\S{3,})"
    ),
    re.IGNORECASE,
)
_UNICODE_LEET = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
)
_CLEAN_RE = re.compile(r"[^a-z0-9 @._'-]+")


def _normalize(text: str) -> str:
    lowered = text.lower().translate(_UNICODE_LEET)
    return _CLEAN_RE.sub("", lowered)


def _contains_blocked(text: str) -> bool:
    lowered = _normalize(text)
    for word in _BLOCKED_WORDS:
        if word.lower() in lowered:
            return True
    return False


class RateLimiter:
    """Per-connection message flood guard (ws 60 msg/s budget for the room)."""

    def __init__(self, window_sec: float = 10.0, max_messages: int = 30) -> None:
        self._window = window_sec
        self._max = max_messages
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def ok(self, key: str) -> bool:
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > self._window:
            window.popleft()
        if len(window) >= self._max:
            return False
        window.append(now)
        return True


def moderate(body: str, limiter: RateLimiter, conn_id: str) -> tuple[str, list[str]]:
    """Return ``(mod_flags, reason)``. A withhold reason means the message is blocked.

    A message is either delivered (no reason), *reviewed* (delivered with a
    ``review`` flag), or *blocked* (```withheld`` and returned to the sender).
    """
    if not body.strip():
        return "empty", []
    if len(body) > 1000:
        return "too_long", []
    if _contains_blocked(body):
        return "blocked", ["blocked", "profanity"]
    flags: list[str] = []
    if _CONTACT_RE.search(body):
        flags.append("review")
    if not limiter.ok(conn_id):
        return "rate_limited", ["blocked", "rate"]
    return "delivered", flags


def classifier_url() -> str | None:
    """Return a configured hosted classifier hook, if any (moderation TAAS)."""
    from worldview.config import get_settings

    url = get_settings().moderation_classifier_url
    return url or None


__all__ = ["RateLimiter", "moderate", "classifier_url"]
