"""FastAPI dependency injection — session, auth, role guards."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import decode_session_token
from app.core.errors import OmniError
from app.db.base import SessionLocal
from app.db.models import User


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session; close on teardown."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def get_current_user(
    db: DbDep,
    omniview_session: Annotated[str | None, Cookie()] = None,
) -> User:
    """Decode the httpOnly session cookie and return the authenticated User.

    Raises HTTP 401 when the cookie is absent or the token is invalid/expired.
    """
    if omniview_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        user_id = decode_session_token(omniview_session)
    except OmniError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
        ) from exc

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Role guards
# ---------------------------------------------------------------------------


def require_admin(current_user: CurrentUser) -> User:
    """Allow only users with role 'admin'."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


def require_reviewer(current_user: CurrentUser) -> User:
    """Allow users with role 'admin' or 'reviewer'."""
    if current_user.role not in {"admin", "reviewer"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer role required",
        )
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]
ReviewerUser = Annotated[User, Depends(require_reviewer)]
