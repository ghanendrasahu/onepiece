"""Auth routes: register, login, refresh, session management, logout."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ulid import new as new_ulid
from worldview.auth import (
    create_access_token,
    generate_refresh_token,
    get_current_user,
    hash_password,
    hash_refresh_token,
    needs_rehash,
    verify_password,
)
from worldview.db import get_db

from ..models import MfaDevice, User
from ..models import Session as SessionRow
from ..schemas import (
    LoginIn,
    MfaEnrollOut,
    MfaVerifyIn,
    MfaVerifyOut,
    RefreshIn,
    RegisterIn,
    TokenOut,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _build_token(user: User, db: Session) -> TokenOut:
    session_id = str(new_ulid())
    refresh_raw = generate_refresh_token()
    session_row = SessionRow(
        id=session_id,
        user_id=user.id,
        expires_at=_refresh_expiry(),
        refresh_token_hash=hash_refresh_token(refresh_raw),
    )
    db.add(session_row)
    access = create_access_token(user.id, scopes=["user"], session_id=session_id)
    db.flush()
    return TokenOut(access_token=access, refresh_token=refresh_raw, user_id=user.id)


def _session_expiry(ttl_days: int = 30) -> datetime:
    return datetime.now(UTC) + timedelta(days=ttl_days)


def _refresh_expiry() -> datetime:
    from worldview.config import get_settings

    return _session_expiry(get_settings().jwt_refresh_ttl_days)


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
    if payload.provider:
        return _social_login(payload, db)
    if not payload.email or not payload.password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="email and password required, or provider and code",
        )
    user = db.execute(
        select(User).where(User.email == str(payload.email).lower())
    ).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    return _build_token(user, db)


def _social_login(payload: LoginIn, db: Session) -> TokenOut:
    """OIDC-style social login (docs/06 §3): exchange a provider code for a user.

    ``code`` is verified against a fixed shared secret in dev; a real
    deployment swaps this for the provider's token-endpoint exchange. A user is
    matched by email when present, otherwise provisioned on first sign-in.
    """
    from worldview.config import get_settings

    if not payload.code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="code required"
        )
    if payload.code != get_settings().social_login_client_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid social login code"
        )
    if payload.email:
        user = db.execute(
            select(User).where(User.email == str(payload.email).lower())
        ).scalar_one_or_none()
        if user is None:
            user = User(
                id=str(new_ulid()),
                email=str(payload.email).lower(),
                password_hash=hash_password(f"social:{payload.provider}:{new_ulid()}"),
                display_name=str(payload.email).split("@")[0],
                locale="en",
            )
            db.add(user)
            db.flush()
        return _build_token(user, db)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="email required to resolve social login",
    )


@router.post("/refresh", response_model=TokenOut)
def refresh(payload: RefreshIn, db: Session = Depends(get_db)) -> TokenOut:
    digest = hash_refresh_token(payload.refresh_token)
    row = db.execute(
        select(SessionRow).where(SessionRow.refresh_token_hash == digest)
    ).scalar_one_or_none()
    exp = row.expires_at if row is not None else None
    if exp is not None and exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    if row is None or row.revoked_at is not None or exp is None or exp < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        )
    user = db.get(User, row.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    new_raw = generate_refresh_token()
    row.refresh_token_hash = hash_refresh_token(new_raw)
    row.expires_at = _refresh_expiry()
    access = create_access_token(user.id, scopes=["user"], session_id=row.id)
    db.flush()
    return TokenOut(access_token=access, refresh_token=new_raw, user_id=user.id)


@router.post("/mfa/enroll", response_model=MfaEnrollOut)
def enroll_mfa(
    current: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MfaEnrollOut:
    """Generate a TOTP secret; the user must verify it once via /mfa/verify."""
    import pyotp

    device = (
        db.execute(select(MfaDevice).where(MfaDevice.user_id == current["sub"])).scalars().first()
    )
    secret = pyotp.random_base32()
    if device is None:
        device = MfaDevice(id=str(new_ulid()), user_id=current["sub"], secret=secret)
        db.add(device)
    else:
        device.secret = secret
        device.is_active = False
    db.flush()
    totp = pyotp.TOTP(secret)
    return MfaEnrollOut(
        secret=secret,
        otpauth_url=totp.provisioning_uri(name=current["sub"], issuer_name="WorldView VR"),
        verified=device.is_active,
    )


@router.post("/mfa/verify", response_model=MfaVerifyOut)
def verify_mfa(
    code: MfaVerifyIn,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MfaVerifyOut:
    import pyotp

    device = (
        db.execute(select(MfaDevice).where(MfaDevice.user_id == claims["sub"])).scalars().first()
    )
    if device is None:
        raise HTTPException(status_code=404, detail="MFA not enrolled")
    if not pyotp.TOTP(device.secret).verify(code.code):
        raise HTTPException(status_code=401, detail="Invalid code")
    device.is_active = True
    device.activated_at = datetime.now(UTC)
    db.flush()
    return MfaVerifyOut(verified=True)


@router.post("/logout")
def logout(
    current: dict = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict[str, str]:
    session_id = current.get("sid")
    if session_id:
        row = db.get(SessionRow, session_id)
        if row is not None:
            row.revoked_at = datetime.now(UTC)
    return {"status": "ok"}
