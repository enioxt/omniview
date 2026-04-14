"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])

_VERSION = "0.1.0"


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health() -> HealthResponse:
    """Return service liveness status and version."""
    return HealthResponse(status="ok", version=_VERSION)
