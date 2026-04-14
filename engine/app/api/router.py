"""Assemble all API routers into a single APIRouter."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes_auth import router as auth_router
from app.api.routes_events import router as events_router
from app.api.routes_health import router as health_router
from app.api.routes_videos import router as videos_router

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(videos_router)
api_router.include_router(events_router)
