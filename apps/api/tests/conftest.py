import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-bytes-long-1234567890")
os.environ.setdefault("BOOTSTRAP_ENABLED", "true")
os.environ.setdefault("AUTH_RATE_LIMIT_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import redis_client as redis_client_module
from app.db.base import Base
from app.db.session import get_db
from app.main import app


class FakeRedis:
    """Minimal in-memory stand-in for redis-py used in tests, so the
    auth rate limiter and any Redis-backed logic run without a real
    Redis server.
    """

    def __init__(self) -> None:
        self._store: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self._store[key] = self._store.get(key, 0) + 1
        return self._store[key]

    def expire(self, key: str, seconds: int) -> None:
        return None


@pytest.fixture()
def db_session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield TestingSessionLocal
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session_factory, monkeypatch):
    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(redis_client_module, "get_redis", lambda: FakeRedis())

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def bootstrap_and_login(client: TestClient, *, email: str, workspace_name: str) -> dict:
    resp = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "full_name": "Test Owner",
            "workspace_name": workspace_name,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def register_and_create_workspace(client: TestClient, *, email: str, workspace_name: str) -> dict:
    """Independent-tenant helper: registers a brand new, unrelated
    user account (not the one-time bootstrap flow) and has them
    create their own workspace, becoming its Administrator.
    """
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "full_name": "Test Owner",
        },
    )
    assert resp.status_code == 201, resp.text
    tokens = resp.json()

    ws_resp = client.post(
        "/api/v1/workspaces",
        json={"name": workspace_name},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert ws_resp.status_code == 201, ws_resp.text
    return tokens
