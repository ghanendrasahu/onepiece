"""JWT access tokens and password hashing (dependency-free crypto primitives)."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from worldview.config import Settings, get_settings

_BEARER = HTTPBearer(auto_error=False)

_PBKDF2_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 (600k iterations).

    Note: production should migrate to argon2id; this is the stdlib default.
    Format: ``pbkdf2$<iterations>$<salt_hex>$<hash_hex>``.
    """
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time comparison of a password against a stored hash."""
    try:
        scheme, iterations, salt_hex, hash_hex = stored.split("$")
        if scheme != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


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


def decode_access_token(token: str, settings: Settings | None = None) -> dict:
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
) -> dict:
    """FastAPI dependency resolving the authenticated user claims."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return decode_access_token(credentials.credentials, settings)


def generate_refresh_token() -> str:
    """Return a high-entropy opaque refresh token (only its hash is persisted)."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """Return a SHA-256 digest for storing/looking up a refresh token."""
    return hashlib.sha256(token.encode()).hexdigest()
