"""Notification routes (docs/06-api-specification.md §11).

Subscribe registers an APNs/FCM/web push token scoped to topics. The test
endpoint walks a mock push provider (deterministic, offline-friendly) and logs
every delivery — production swaps in FCM/APNs behind the same log row.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ulid import new as new_ulid
from worldview.auth import get_current_user
from worldview.db import get_db

from ..models import NotificationLog, PushSubscription
from ..schemas import (
    SubscribeIn,
    SubscribeOut,
    TestNotificationIn,
    TestNotificationOut,
)

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])


def _topics_csv(topics: list[str]) -> str:
    return ",".join(sorted(set(topics)))


@router.post("/subscribe", response_model=SubscribeOut, status_code=201)
def subscribe(
    payload: SubscribeIn,
    claims: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PushSubscription:
    """Register (or upsert) a push token for the authenticated user."""
    from sqlalchemy import select

    existing = db.execute(
        select(PushSubscription).where(
            PushSubscription.user_id == claims["sub"],
            PushSubscription.push_token == payload.push_token,
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.platform = payload.platform
        existing.topics = _topics_csv(payload.topics)
        existing.disabled = False
        db.commit()
        db.refresh(existing)
        return existing

    sub = PushSubscription(
        id=str(new_ulid()),
        user_id=claims["sub"],
        platform=payload.platform,
        push_token=payload.push_token,
        topics=_topics_csv(payload.topics),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.post("/test", response_model=TestNotificationOut, status_code=201)
def test_notification(
    payload: TestNotificationIn,
    claims: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationLog:
    """Send a test push to every live subscription the user owns (T1)."""
    from sqlalchemy import select

    subscriptions = db.execute(
        select(PushSubscription).where(
            PushSubscription.user_id == claims["sub"],
            PushSubscription.disabled.is_(False),
        )
    ).scalars()

    log = NotificationLog(
        id=str(new_ulid()),
        user_id=claims["sub"],
        topic=payload.topic,
        title=f"WorldView test ({payload.topic})",
        body="This is a test notification.",
        provider="mock",
        status="sent",
    )
    db.add(log)
    db.flush()
    for sub in subscriptions:
        db.add(
            NotificationLog(
                id=str(new_ulid()),
                user_id=claims["sub"],
                topic=payload.topic,
                title=f"WorldView test ({payload.topic})",
                body="This is a test notification.",
                provider=f"mock:{sub.platform}",
                status="sent",
            )
        )
    db.commit()
    db.refresh(log)
    return log
