"""Authentication endpoints — login, logout, me."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_db
from app.core.auth import create_session_token, verify_password
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_NAME = "omniview_session"
_COOKIE_MAX_AGE = 60 * 60 * 8  # 8 hours


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    user_id: str
    username: str
    role: str


class MeResponse(BaseModel):
    user_id: str
    username: str
    role: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate and receive session cookie",
)
async def login(
    body: LoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    """Verify credentials and set an httpOnly session cookie."""
    user: User | None = (
        db.query(User).filter(User.username == body.username).first()
    )

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_session_token(str(user.id))

    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        secure=False,  # set to True behind HTTPS in production
    )

    return LoginResponse(
        user_id=str(user.id),
        username=user.username,
        role=user.role,
    )


@router.post("/logout", summary="Clear session cookie")
async def logout(response: Response) -> dict[str, str]:
    """Expire the session cookie."""
    response.delete_cookie(key=_COOKIE_NAME)
    return {"detail": "Logged out"}


@router.get("/me", response_model=MeResponse, summary="Current user info")
async def me(current_user: CurrentUser) -> MeResponse:
    """Return the identity of the authenticated caller."""
    return MeResponse(
        user_id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
    )
