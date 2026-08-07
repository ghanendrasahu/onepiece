"""Auth routes: register, login, session management."""

from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ulid import new as new_ulid
from worldview.auth import create_access_token, hash_password, verify_password
from worldview.db import get_db

from ..models import Session as SessionRow
from ..models import User
from ..schemas import LoginIn, RegisterIn, TokenOut

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _build_token(user: User, db: Session) -> TokenOut:
    session_row = SessionRow(
        id=str(new_ulid()),
        user_id=user.id,
        expires_at=_session_expiry(),
    )
    db.add(session_row)
    token = create_access_token(user.id, scopes=["user"])
    db.flush()
    return TokenOut(access_token=token, user_id=user.id)


def _session_expiry():
    from datetime import datetime, timedelta

    return datetime.now(UTC) + timedelta(days=30)


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        id=str(new_ulid()),
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        locale=payload.locale,
    )
    db.add(user)
    db.flush()  # persist the user first so its session INSERT satisfies the FK
    return _build_token(user, db)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.execute(
        select(User).where(User.email == str(payload.email).lower())
    ).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _build_token(user, db)


@router.post("/logout")
def logout(db: Session = Depends(get_db)) -> dict[str, str]:
    return {"status": "ok"}
