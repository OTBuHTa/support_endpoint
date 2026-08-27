from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import redis_client
from app.db.session import get_db
from app.version import API_VERSION, BUILD_REVISION

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness — process is up. Never touches dependencies."""
    return {"status": "ok", "version": API_VERSION, "build_revision": BUILD_REVISION}


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    """Readiness — required database and Redis dependencies are reachable."""
    checks = {"database": "ok", "redis": "ok"}
    status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "unavailable"
        status = "degraded"

    try:
        redis_client.get_redis().ping()
    except Exception:
        checks["redis"] = "unavailable"
        status = "degraded"

    return {
        "status": status,
        "checks": checks,
        "version": API_VERSION,
        "build_revision": BUILD_REVISION,
    }
