"""Auth utilities — bcrypt password hashing + session management.

Uses itsdangerous SignedSerializer for tamper-evident session cookies.
Three roles: admin > reviewer > viewer
"""
from __future__ import annotations

import bcrypt as _bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AuthFailed, PermissionDenied
from app.db.models import User

_signer = URLSafeTimedSerializer(settings.secret_key)

ROLE_WEIGHTS = {"admin": 3, "reviewer": 2, "viewer": 1}


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Session token ─────────────────────────────────────────────────────────────

def create_session_token(user_id: str) -> str:
    return _signer.dumps(user_id, salt="session")


def decode_session_token(token: str) -> str:
    """Returns user_id or raises AuthFailed."""
    try:
        return _signer.loads(token, salt="session", max_age=settings.session_max_age)  # type: ignore[return-value]
    except (SignatureExpired, BadSignature) as exc:
        raise AuthFailed() from exc


# ── User helpers ──────────────────────────────────────────────────────────────

def authenticate(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
    if not user or not verify_password(password, user.hashed_password):
        raise AuthFailed()
    return user


def require_role(user: User, min_role: str) -> None:
    """Raise PermissionDenied if user role is below min_role."""
    if ROLE_WEIGHTS.get(user.role, 0) < ROLE_WEIGHTS.get(min_role, 0):
        raise PermissionDenied(action=f"requires role '{min_role}'")


def create_default_admin(db: Session) -> User | None:
    """Create default admin on first run if no users exist."""
    if db.query(User).count() > 0:
        return None
    admin = User(
        username="admin",
        hashed_password=hash_password("omniview"),
        role="admin",
    )
    db.add(admin)
    db.commit()
    return admin
