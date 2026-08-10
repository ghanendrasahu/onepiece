"""Admin & moderation-console routes (FR-10.1, docs/06-api-specification.md §10).

Every route is guarded by the ``admin`` JWT scope. The console reads user and
stream rows read-only from the shared database and writes moderation decisions
plus an immutable admin-audit trail.
"""

from __future__ import annotations

from datetime import UTC, datetime

# Cross-app ORM models used read-only by the admin console. Importing them here
# also registers their tables on the shared metadata so dev ``create_all``
# (tests, local SQLite) builds the full schema alongside moderation's own rows.
import worldview_creators.models as _creators_models  # noqa: F401
import worldview_identity.models as _identity_models  # noqa: F401
import worldview_streaming.models as _streaming_models  # noqa: F401
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from ulid import new as new_ulid
from worldview.auth import require_scope
from worldview.db import get_db

from ..models import AdminAction, ModerationItem
from ..schemas import (
    AdminActionOut,
    AdminUserOut,
    DecisionIn,
    ModerationItemOut,
    SuspendIn,
)

router = APIRouter(prefix="/v1/admin", tags=["admin"])

admin_guard = require_scope("admin")


def _status_for_row(row) -> str:
    if getattr(row, "deleted_at", None) is not None:
        return "deleted"
    return "active"


@router.get("/users", response_model=list[AdminUserOut])
def admin_users(
    q: str | None = None,
    status: str | None = Query(default=None, pattern="^(active|suspended|deleted)$"),
    claims: dict = Depends(admin_guard),
    db: Session = Depends(get_db),
) -> list[AdminUserOut]:
    from worldview_identity.models import User

    stmt = select(User)
    if q:
        stmt = stmt.where(User.email.contains(q.lower(), autoescape=True))
    rows = db.execute(stmt.order_by(User.created_at.desc()).limit(500)).scalars()
    return [
        AdminUserOut(
            id=u.id,
            email=u.email,
            display_name=u.display_name,
            status=_status_for_row(u),
            is_verified=u.is_verified,
        )
        for u in rows
    ]


@router.post("/users/{user_id}/suspend", response_model=AdminUserOut)
def suspend_user(
    user_id: str,
    payload: SuspendIn,
    claims: dict = Depends(admin_guard),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    from worldview_identity.models import User

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    action = AdminAction(
        id=str(new_ulid()),
        admin_id=claims["sub"],
        action="suspend",
        target_type="user",
        target_id=user_id,
        note=f"{payload.reason} (duration_hours={payload.duration_hours})",
    )
    db.add(action)
    db.commit()
    return AdminUserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        status="suspended",
        is_verified=user.is_verified,
    )


@router.get("/streams", response_model=list[dict])
def admin_streams(
    claims: dict = Depends(admin_guard),
    db: Session = Depends(get_db),
) -> list[dict]:
    from worldview_streaming.models import StreamSession

    rows = db.execute(
        select(StreamSession).order_by(StreamSession.created_at.desc()).limit(500)
    ).scalars()
    return [
        {
            "id": s.id,
            "tour_id": s.tour_id,
            "creator_id": s.creator_id,
            "status": s.status,
            "region_key": s.region_key,
            "created_at": s.created_at.isoformat(),
        }
        for s in rows
    ]


@router.get("/moderation/queue", response_model=list[ModerationItemOut])
def moderation_queue(
    claims: dict = Depends(admin_guard),
    db: Session = Depends(get_db),
) -> list[ModerationItem]:
    rows = db.execute(
        select(ModerationItem)
        .where(ModerationItem.decision.is_(None))
        .order_by(ModerationItem.risk_score.desc(), ModerationItem.created_at.asc())
    ).scalars()
    return list(rows)


@router.post("/moderation/{item_id}/decision", response_model=ModerationItemOut)
def moderation_decision(
    item_id: str,
    payload: DecisionIn,
    claims: dict = Depends(admin_guard),
    db: Session = Depends(get_db),
) -> ModerationItem:
    item = db.get(ModerationItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Moderation item not found")

    item.decision = payload.decision
    item.reviewed_by = claims["sub"]
    item.reviewed_at = datetime.now(UTC)

    action = AdminAction(
        id=str(new_ulid()),
        admin_id=claims["sub"],
        action=f"decision:{payload.decision}",
        target_type=item.object_type,
        target_id=item.object_id,
        note=payload.note,
    )
    db.add(action)
    db.commit()
    db.refresh(item)
    return item


@router.get("/creators", response_model=list[dict])
def admin_creators(
    q: str | None = None,
    status: str | None = Query(default=None, pattern="^(applied|verified|rejected)$"),
    claims: dict = Depends(admin_guard),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Creator profiles across the platform (FR-10.1)."""
    from worldview_creators.models import CreatorProfile

    stmt = select(CreatorProfile)
    if status:
        stmt = stmt.where(CreatorProfile.status == status)
    rows = db.execute(stmt.order_by(CreatorProfile.created_at.desc()).limit(500)).scalars()
    return [
        {
            "user_id": p.user_id,
            "status": p.status,
            "region": p.region,
            "equipment": p.equipment,
            "verified_at": p.verified_at.isoformat() if p.verified_at else None,
            "created_at": p.created_at.isoformat(),
        }
        for p in rows
    ]


@router.get("/payouts", response_model=list[dict])
def admin_payouts(
    status: str | None = Query(default=None, pattern="^(pending|paid|failed)$"),
    claims: dict = Depends(admin_guard),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Payout ledger across creators (FR-10.1)."""
    from worldview_creators.models import Payout

    stmt = select(Payout)
    if status:
        stmt = stmt.where(Payout.status == status)
    rows = db.execute(stmt.order_by(Payout.created_at.desc()).limit(500)).scalars()
    return [
        {
            "id": p.id,
            "creator_id": p.creator_id,
            "amount_cents": p.amount_cents,
            "currency": p.currency,
            "status": p.status,
            "provider_tx_id": p.provider_tx_id,
            "created_at": p.created_at.isoformat(),
        }
        for p in rows
    ]


@router.get("/actions", response_model=list[AdminActionOut])
def admin_actions(
    claims: dict = Depends(admin_guard),
    db: Session = Depends(get_db),
) -> list[AdminAction]:
    rows = db.execute(
        select(AdminAction).order_by(AdminAction.created_at.desc()).limit(200)
    ).scalars()
    return list(rows)
