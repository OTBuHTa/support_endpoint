import logging
import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.observability.logging import configure_logging
from app.repositories.workspace_repo import WorkspaceRepository
from app.services.operations_service import OperationsService

LOGGER = logging.getLogger("csp.sla_scheduler")
ADVISORY_LOCK_ID = 73108201


def evaluate_all_workspaces(db: Session) -> tuple[int, int, int, int]:
    workspaces = WorkspaceRepository(db).list_all()
    evaluated = warnings = breaches = 0
    for workspace in workspaces:
        try:
            workspace_evaluated, workspace_warnings, workspace_breaches = OperationsService(
                db
            ).evaluate_sla(workspace_id=workspace.id)
            evaluated += workspace_evaluated
            warnings += workspace_warnings
            breaches += workspace_breaches
        except Exception:
            db.rollback()
            LOGGER.exception(
                "sla_scheduler_workspace_failed",
                extra={"workspace_id": workspace.id},
            )
    return len(workspaces), evaluated, warnings, breaches


def _try_lock(db: Session) -> bool:
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return True
    return bool(
        db.scalar(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": ADVISORY_LOCK_ID},
        )
    )


def _unlock(db: Session) -> None:
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return
    db.execute(
        text("SELECT pg_advisory_unlock(:lock_id)"),
        {"lock_id": ADVISORY_LOCK_ID},
    )


def run_once() -> None:
    db = SessionLocal()
    locked = False
    try:
        locked = _try_lock(db)
        if not locked:
            LOGGER.info("sla_scheduler_skipped_lock_held")
            return
        workspaces, evaluated, warnings, breaches = evaluate_all_workspaces(db)
        LOGGER.info(
            "sla_scheduler_cycle_completed",
            extra={
                "workspaces": workspaces,
                "evaluated": evaluated,
                "warnings_created": warnings,
                "breaches_created": breaches,
            },
        )
    finally:
        if locked:
            try:
                _unlock(db)
            except Exception:
                LOGGER.exception("sla_scheduler_unlock_failed")
        db.close()


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    interval = max(10, settings.sla_scheduler_interval_seconds)
    LOGGER.info("sla_scheduler_started", extra={"interval_seconds": interval})
    while True:
        started = time.monotonic()
        try:
            run_once()
        except Exception:
            LOGGER.exception("sla_scheduler_cycle_failed")
        elapsed = time.monotonic() - started
        time.sleep(max(1.0, interval - elapsed))


if __name__ == "__main__":
    main()
