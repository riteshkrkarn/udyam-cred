"""Authentication helpers: bcrypt password hashing and JWT access tokens.

Refresh tokens are opaque, DB-stored and hashed (sha256); rotation is handled by
the API layer in app/main.py using the RefreshToken model. Access tokens are
short-lived JWTs (default 15 minutes). "Remember me" extends the refresh token
lifetime to 1 day.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings
from app.utils import utcnow_naive


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the password (utf-8 encoded, stored as str)."""
    if not isinstance(password, str):
        raise ValueError("password must be a string")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """True if password matches the stored bcrypt hash; never raises."""
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    """Create a signed JWT access token. subject is the user id as a string."""
    minutes = expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT, returning its claims. Raises on invalid/expired."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def create_refresh_token_value() -> str:
    """Generate a new opaque refresh token value (urlsafe, ~64 chars)."""
    return secrets.token_urlsafe(48)


def hash_token(value: str) -> str:
    """Hash a refresh token value for storage (sha256 hex)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def refresh_expiry(remember_me: bool) -> datetime:
    """Refresh-token expiry datetime (naive UTC). Remember me = 1 day, else 1 hour."""
    hours = settings.REMEMBER_ME_EXPIRE_HOURS if remember_me else settings.REFRESH_TOKEN_EXPIRE_HOURS
    return utcnow_naive() + timedelta(hours=hours)
