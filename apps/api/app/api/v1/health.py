from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.version import API_VERSION

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness — process is up. Never touches dependencies."""
    return {"status": "ok", "version": API_VERSION}


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    """Readiness — dependencies (database) are reachable."""
    checks = {"database": "ok"}
    status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "unavailable"
        status = "degraded"
    return {"status": status, "checks": checks, "version": API_VERSION}
