from sqlalchemy.orm import Session

from app.authz.permissions import ROLE_ADMINISTRATOR
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories.audit_repo import AuditRepository
from app.repositories.workspace_repo import MembershipRepository, WorkspaceRepository
from app.services.auth_service import ensure_system_roles


class WorkspaceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.workspaces = WorkspaceRepository(db)
        self.memberships = MembershipRepository(db)
        self.audit = AuditRepository(db)

    def create_workspace_for_user(self, *, user: User, name: str) -> Workspace:
        role_ids = ensure_system_roles(self.db)
        workspace = self.workspaces.create(name=name)
        self.memberships.create(
            workspace_id=workspace.id,
            user_id=user.id,
            role_id=role_ids[ROLE_ADMINISTRATOR],
        )
        self.audit.record(
            action="workspace.created",
            workspace_id=workspace.id,
            actor_user_id=user.id,
            resource_type="workspace",
            resource_id=workspace.id,
        )
        self.db.commit()
        return workspace

    def list_workspaces_for_user(self, *, user: User) -> list[Workspace]:
        return self.workspaces.list_for_user(user.id)
