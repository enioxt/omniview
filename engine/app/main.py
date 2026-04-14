"""OmniView FastAPI application entry point."""

from __future__ import annotations

import pathlib
import re
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.errors import OmniError
from app.observability.logging import configure_logging
from app.db.base import engine
from app.db.models import Base
from app.core.auth import create_default_admin

_UI_DIST = pathlib.Path(__file__).parent.parent / "ui" / "dist"
from app.core.config import settings as _settings
_DATA_DIR = _settings.storage_path / "data"
_ASSETS_DIR = _DATA_DIR / "assets"


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: create dirs, run migrations, seed admin, configure logging."""
    configure_logging()

    # Ensure data directories exist
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # Run alembic upgrade head
    from alembic import command
    from alembic.config import Config as AlembicConfig

    alembic_cfg = AlembicConfig(
        str(pathlib.Path(__file__).parent.parent / "alembic.ini")
    )
    command.upgrade(alembic_cfg, "head")

    # Seed default admin if absent
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        create_default_admin(db)

    yield


# ---------------------------------------------------------------------------
# CORS origin list
# ---------------------------------------------------------------------------


def _build_cors_origins() -> list[str]:
    """Allow localhost on common dev ports plus 192.168.x.x/y.y."""
    origins: list[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    return origins


def _is_allowed_origin(origin: str) -> bool:
    """Return True for localhost or 192.168 addresses (any port)."""
    return bool(
        re.match(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$", origin)
        or re.match(r"^https?://192\.168\.\d{1,3}\.\d{1,3}(:\d+)?$", origin)
    )


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title="OmniView",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_build_cors_origins(),
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3})(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(api_router)

    # Metrics endpoint
    @app.get("/api/metrics", tags=["observability"], include_in_schema=False)
    async def metrics() -> dict[str, Any]:
        from app.observability.metrics import collect_metrics

        return await collect_metrics()

    # Global error handler for OmniError
    @app.exception_handler(OmniError)
    async def omni_error_handler(request: Request, exc: OmniError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    # Serve SPA — only if the build exists (skip in test/dev without a build)
    if _UI_DIST.is_dir():
        app.mount("/", StaticFiles(directory=str(_UI_DIST), html=True), name="spa")

    return app


app = create_app()
