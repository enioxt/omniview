"""Integration tests for FastAPI endpoints.

Uses an in-memory SQLite database and the test client.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.auth import hash_password
from app.db.base import Base
from app.db.models import User
from app.main import create_app

_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(_ENGINE)
_Session = sessionmaker(bind=_ENGINE, autocommit=False, autoflush=False)

# Seed test user once
with _Session() as db:
    db.add(User(
        username="testadmin",
        hashed_password=hash_password("testpass"),
        role="admin",
    ))
    db.commit()


def override_db():  # type: ignore[return]
    db = _Session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client() -> TestClient:  # type: ignore[return]
    app = create_app()
    app.dependency_overrides[get_db] = override_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c  # type: ignore[misc]


def test_health(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_success(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"username": "testadmin", "password": "testpass"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["username"] == "testadmin"
    assert data["role"] == "admin"
    assert "omniview_session" in r.cookies


def test_login_wrong_password(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"username": "testadmin", "password": "wrong"})
    assert r.status_code == 401


def test_me_unauthenticated() -> None:
    # Use a fresh client with no cookies
    app = create_app()
    app.dependency_overrides[get_db] = override_db
    with TestClient(app, raise_server_exceptions=False) as fresh:
        r = fresh.get("/api/auth/me")
    assert r.status_code == 401


def test_list_videos_unauthenticated() -> None:
    app = create_app()
    app.dependency_overrides[get_db] = override_db
    with TestClient(app, raise_server_exceptions=False) as fresh:
        r = fresh.get("/api/videos")
    assert r.status_code == 401


def test_list_videos_authenticated(client: TestClient) -> None:
    client.post("/api/auth/login", json={"username": "testadmin", "password": "testpass"})
    r = client.get("/api/videos")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
