from app.repositories.workspace_repo import WorkspaceRepository
from app.workers.sla_scheduler import evaluate_all_workspaces


def test_scheduler_handles_empty_database(db_session_factory):
    db = db_session_factory()
    try:
        assert evaluate_all_workspaces(db) == (0, 0, 0, 0)
    finally:
        db.close()


def test_scheduler_sweeps_all_workspaces(db_session_factory):
    db = db_session_factory()
    try:
        WorkspaceRepository(db).create(name="First")
        WorkspaceRepository(db).create(name="Second")
        db.commit()

        workspaces, evaluated, warnings, breaches = evaluate_all_workspaces(db)
        assert workspaces == 2
        assert evaluated == 0
        assert warnings == 0
        assert breaches == 0
    finally:
        db.close()
