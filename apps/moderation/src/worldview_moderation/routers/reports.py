"""Safety reporting routes (FR-9.3): users & stream viewing reports."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ulid import new as new_ulid
from worldview.auth import get_current_user
from worldview.db import get_db

from ..models import ModerationItem
from ..schemas import ModerationItemOut, ReportIn

router = APIRouter(prefix="/v1", tags=["reports"])

_logger = logging.getLogger("worldview_moderation.reports")


@router.post("/reports", response_model=ModerationItemOut, status_code=201)
def create_report(
    payload: ReportIn,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModerationItem:
    """Record a user report; creates a queued moderation item.

    Deduplicates: repeated reports for the same object by the same reporter
    bump an existing pending item's score instead of creating a new row.
    """
    from sqlalchemy import select

    existing = db.execute(
        select(ModerationItem).where(
            ModerationItem.object_type == payload.object_type,
            ModerationItem.object_id == payload.object_id,
            ModerationItem.reporter_id == claims["sub"],
            ModerationItem.decision.is_(None),
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.risk_score = min(1.0, (existing.risk_score or 0.0) + 0.1)
        db.commit()
        db.refresh(existing)
        return existing

    item = ModerationItem(
        id=str(new_ulid()),
        object_type=payload.object_type,
        object_id=payload.object_id,
        reporter_id=claims["sub"],
        reason=payload.reason,
        risk_score=0.5,
        auto_flag=False,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    _logger.info(
        "report created", extra={"object_type": item.object_type, "object_id": item.object_id}
    )
    return item


@router.get("/reports/mine", response_model=list[ModerationItemOut])
def my_reports(
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ModerationItem]:
    from sqlalchemy import select

    rows = db.execute(
        select(ModerationItem)
        .where(ModerationItem.reporter_id == claims["sub"])
        .order_by(ModerationItem.created_at.desc())
    ).scalars()
    return list(rows)
