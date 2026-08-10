"""Authenticated user routes: profile, sessions, consent registry, GDPR."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from worldview.auth import get_current_user
from worldview.db import get_db

from ..models import ConsentRecord, User
from ..models import Session as SessionRow
from ..schemas import (
    ConsentIn,
    ConsentOut,
    GdprDeleteOut,
    GdprExportOut,
    SessionOut,
    UserOut,
)

router = APIRouter(prefix="/v1/users/me", tags=["me"])

_DELETED_EMAIL_DOMAIN = "deleted.worldview.vr"


@router.get("", response_model=UserOut)
def me(
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, claims["sub"])
    if user is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SessionRow]:
    rows = db.execute(
        select(SessionRow)
        .where(SessionRow.user_id == claims["sub"])
        .order_by(SessionRow.created_at.desc())
    ).scalars()
    return list(rows)


@router.get("/consents", response_model=list[ConsentOut])
def list_consents(
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConsentRecord]:
    rows = db.execute(select(ConsentRecord).where(ConsentRecord.user_id == claims["sub"])).scalars()
    return list(rows)


@router.post("/consents", response_model=ConsentOut, status_code=201)
def record_consent(
    payload: ConsentIn,
    request: Request,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsentOut:
    from fastapi import HTTPException

    row = db.get(ConsentRecord, (claims["sub"], payload.policy_id))
    if not payload.accepted:
        if row is None:
            raise HTTPException(status_code=404, detail="Consent not recorded")
        db.delete(row)
        db.flush()
        return ConsentOut(policy_id=payload.policy_id, accepted_at=datetime.now(UTC))
    if row is None:
        row = ConsentRecord(
            user_id=claims["sub"],
            policy_id=payload.policy_id,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(row)
        db.flush()
    return ConsentOut(policy_id=row.policy_id, accepted_at=row.accepted_at)


@router.post("/gdpr/export", response_model=GdprExportOut)
def gdpr_export(
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GdprExportOut:
    """Build the user's full data subject export (SRS FR-1.4)."""
    user = db.get(User, claims["sub"])
    if user is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="User not found")
    sessions = db.execute(select(SessionRow).where(SessionRow.user_id == claims["sub"])).scalars()
    consents = db.execute(
        select(ConsentRecord).where(ConsentRecord.user_id == claims["sub"])
    ).scalars()
    data: dict[str, Any] = {
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "locale": user.locale,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "sessions": [
            {
                "id": s.id,
                "device_id": s.device_id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "revoked": s.revoked_at is not None,
            }
            for s in sessions
        ],
        "consents": [
            {
                "policy_id": c.policy_id,
                "accepted_at": c.accepted_at.isoformat() if c.accepted_at else None,
            }
            for c in consents
        ],
    }
    return GdprExportOut(export_id=f"export-{user.id}", status="ready", data=data)


@router.post("/gdpr/delete", response_model=GdprDeleteOut)
def gdpr_delete(
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GdprDeleteOut:
    """Right-to-erasure: revoke sessions, redact PII, soft-delete account."""
    user = db.get(User, claims["sub"])
    if user is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="User not found")
    now = datetime.now(UTC)

    sessions = db.execute(select(SessionRow).where(SessionRow.user_id == user.id)).scalars()
    for session_row in sessions:
        session_row.revoked_at = now

    user.email = f"{user.id}@{_DELETED_EMAIL_DOMAIN}"
    user.password_hash = ""
    user.display_name = "[deleted account]"
    user.deleted_at = now
    db.flush()

    consents = db.execute(select(ConsentRecord).where(ConsentRecord.user_id == user.id)).scalars()
    for consent in consents:
        db.delete(consent)
    return GdprDeleteOut(job_id=f"delete-{user.id}", status="completed")
