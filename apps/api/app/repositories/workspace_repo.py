import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workspace import Workspace, WorkspaceMembership


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "workspace"


class WorkspaceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, workspace_id: str) -> Workspace | None:
        return self.db.get(Workspace, workspace_id)

    def get_by_slug(self, slug: str) -> Workspace | None:
        stmt = select(Workspace).where(Workspace.slug == slug)
        return self.db.scalar(stmt)

    def create(self, *, name: str) -> Workspace:
        base_slug = slugify(name)
        slug = base_slug
        suffix = 1
        while self.get_by_slug(slug) is not None:
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        workspace = Workspace(name=name, slug=slug)
        self.db.add(workspace)
        self.db.flush()
        return workspace

    def list_for_user(self, user_id: str) -> list[Workspace]:
        stmt = (
            select(Workspace)
            .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
            .where(WorkspaceMembership.user_id == user_id)
        )
        return list(self.db.scalars(stmt))


class MembershipRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, *, workspace_id: str, user_id: str) -> WorkspaceMembership | None:
        stmt = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def create(self, *, workspace_id: str, user_id: str, role_id: str) -> WorkspaceMembership:
        membership = WorkspaceMembership(
            workspace_id=workspace_id, user_id=user_id, role_id=role_id
        )
        self.db.add(membership)
        self.db.flush()
        return membership
