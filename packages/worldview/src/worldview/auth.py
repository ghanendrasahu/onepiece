"""JWT access tokens and password hashing (argon2id with legacy PBKDF2 verify)."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from worldview.config import Settings, get_settings

_BEARER = HTTPBearer(auto_error=False)

_PBKDF2_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    """Hash a password with argon2id (the current OWASP recommendation).

    Format: the full ``$argon2id$v=19$m=65536,t=3,p=4$...`` PHC string emitted
    by argon2-cffi. New registrations use argon2id; legacy PBKDF2 hashes remain
    verifiable and are opportunistically upgraded on the next successful login.
    """
    from argon2 import PasswordHasher

    return PasswordHasher().hash(password)


def verify_password(password: str, stored: str) -> bool:
    """Verify a password, accepting both argon2id and legacy PBKDF2 hashes."""
    if stored.startswith("pbkdf2$"):
        return _verify_pbkdf2(password, stored)
    if stored.startswith("$argon2"):
        from argon2 import PasswordHasher
        from argon2.exceptions import VerifyMismatchError

        try:
            return PasswordHasher().verify(stored, password)
        except (VerifyMismatchError, ValueError, TypeError):
            return False
    return False


def _verify_pbkdf2(password: str, stored: str) -> bool:
    """Constant-time comparison against a legacy PBKDF2-HMAC-SHA256 hash."""
    try:
        _scheme, iterations, salt_hex, hash_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def needs_rehash(stored: str) -> bool:
    """Return True when a stored hash should be upgraded to argon2id.

    PBKDF2 hashes return True; argon2id hashes return True only if they use
    weaker parameters than the current production profile (so we can re-hash on
    the next login without forcing every user to reset their password).
    """
    if stored.startswith("pbkdf2$"):
        return True
    if stored.startswith("$argon2"):
        from argon2 import PasswordHasher

        return "id$" not in stored or PasswordHasher().check_needs_rehash(stored)
    return True


def create_access_token(
    user_id: str,
    scopes: list[str],
    settings: Settings | None = None,
    session_id: str | None = None,
) -> str:
    """Issue a short-lived JWT access token (audience-scoped)."""
    settings = settings or get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "scopes": scopes,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_access_ttl_minutes)).timestamp()),
        "iss": "worldview",
        "region": settings.region_key,
    }
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    """Decode and validate a JWT, raising on expiry/signature failure."""
    settings = settings or get_settings()
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], issuer="worldview"
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_BEARER),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """FastAPI dependency resolving the authenticated user claims."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return decode_access_token(credentials.credentials, settings)


def require_scope(required: str):
    """Return a FastAPI dependency that demands a JWT scope (e.g. ``admin``).

    Keeps RBAC enforcement cheap and consistent: every guarded route resolves
    the claims then checks membership of ``required`` in ``scopes``.
    """

    def _guarded(claims: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        scopes = set(claims.get("scopes") or [])
        if required not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires scope: {required}",
            )
        return claims

    return _guarded


def generate_refresh_token() -> str:
    """Return a high-entropy opaque refresh token (only its hash is persisted)."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """Return a SHA-256 digest for storing/looking up a refresh token."""
    return hashlib.sha256(token.encode()).hexdigest()
