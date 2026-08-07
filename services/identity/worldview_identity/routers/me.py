"""Authenticated user routes: profile, sessions, GDPR stubs."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from worldview.auth import get_current_user
from worldview.db import get_db

from ..models import Session as SessionRow
from ..models import User
from ..schemas import SessionOut, UserOut

router = APIRouter(prefix="/v1/users/me", tags=["me"])


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


@router.post("/gdpr/export")
def gdpr_export(claims: dict = Depends(get_current_user)) -> dict[str, str]:
    # Production: enqueue async export job on Kafka, return job id.
    return {"job_id": "stub-export-job", "status": "queued"}


@router.post("/gdpr/delete")
def gdpr_delete(claims: dict = Depends(get_current_user)) -> dict[str, str]:
    # Production: enqueue async deletion workflow across all services.
    return {"job_id": "stub-delete-job", "status": "queued"}
