"""Enterprise routes (FR-10.2, docs/06-api-specification.md §10).

Groups, memberships, private virtual events and per-group engagement reports.
Guarded by the ``admin`` scope like the rest of the console.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ulid import new as new_ulid
from worldview.auth import require_scope
from worldview.db import get_db

from ..models import EnterpriseEvent, EnterpriseGroup, EnterpriseGroupMember
from ..schemas import (
    EnterpriseEventIn,
    EnterpriseEventOut,
    EnterpriseGroupIn,
    EnterpriseGroupOut,
    EnterpriseGroupReport,
    EnterpriseMemberOut,
    EnterpriseMembersIn,
)

router = APIRouter(prefix="/v1/enterprise", tags=["enterprise"])

enterprise_guard = require_scope("admin")


def _group_or_404(db: Session, group_id: str) -> EnterpriseGroup:
    group = db.get(EnterpriseGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.post("/groups", response_model=EnterpriseGroupOut, status_code=201)
def create_group(
    payload: EnterpriseGroupIn,
    claims: dict = Depends(enterprise_guard),
    db: Session = Depends(get_db),
) -> EnterpriseGroup:
    group = EnterpriseGroup(id=str(new_ulid()), name=payload.name, owner_id=claims["sub"])
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.post(
    "/groups/{group_id}/members",
    response_model=list[EnterpriseMemberOut],
    status_code=201,
)
def add_members(
    group_id: str,
    payload: EnterpriseMembersIn,
    claims: dict = Depends(enterprise_guard),
    db: Session = Depends(get_db),
) -> list[EnterpriseMemberOut]:
    _group_or_404(db, group_id)
    now = datetime.now(UTC)
    existing = {
        row.user_id
        for row in db.execute(
            select(EnterpriseGroupMember).where(
                EnterpriseGroupMember.group_id == group_id,
                EnterpriseGroupMember.user_id.in_(payload.user_ids),
            )
        ).scalars()
    }
    rows = []
    for user_id in payload.user_ids:
        if user_id in existing:
            continue
        row = EnterpriseGroupMember(group_id=group_id, user_id=user_id, created_at=now)
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


@router.post("/events", response_model=EnterpriseEventOut, status_code=201)
def create_event(
    payload: EnterpriseEventIn,
    claims: dict = Depends(enterprise_guard),
    db: Session = Depends(get_db),
) -> EnterpriseEvent:
    event = EnterpriseEvent(
        id=str(new_ulid()),
        group_id=payload.group_id,
        title=payload.title,
        starts_at=payload.starts_at.replace(tzinfo=payload.starts_at.tzinfo or UTC),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/reports", response_model=list[EnterpriseGroupReport])
def enterprise_reports(
    claims: dict = Depends(enterprise_guard),
    db: Session = Depends(get_db),
) -> list[EnterpriseGroupReport]:
    """Engagement per group: member + event counts (FR-10.2)."""
    member_counts = dict(
        db.execute(
            select(EnterpriseGroupMember.group_id, func.count()).group_by(
                EnterpriseGroupMember.group_id
            )
        ).all()
    )
    event_counts = dict(
        db.execute(
            select(EnterpriseEvent.group_id, func.count()).group_by(EnterpriseEvent.group_id)
        ).all()
    )
    groups = db.execute(
        select(EnterpriseGroup).order_by(EnterpriseGroup.created_at.desc()).limit(500)
    ).scalars()
    return [
        EnterpriseGroupReport(
            group_id=g.id,
            name=g.name,
            members=member_counts.get(g.id, 0),
            events=event_counts.get(g.id, 0),
        )
        for g in groups
    ]
