from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rbac import Permission, Role, RolePermission


class RbacRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_role_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        return self.db.scalar(stmt)

    def create_role(self, *, name: str, description: str = "", is_system: bool = False) -> Role:
        role = Role(name=name, description=description, is_system=is_system)
        self.db.add(role)
        self.db.flush()
        return role

    def get_permission_by_code(self, code: str) -> Permission | None:
        stmt = select(Permission).where(Permission.code == code)
        return self.db.scalar(stmt)

    def create_permission(self, *, code: str, description: str = "") -> Permission:
        permission = Permission(code=code, description=description)
        self.db.add(permission)
        self.db.flush()
        return permission

    def grant(self, *, role_id: str, permission_id: str) -> None:
        existing = self.db.scalar(
            select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        )
        if existing is not None:
            return
        self.db.add(RolePermission(role_id=role_id, permission_id=permission_id))
        self.db.flush()

    def permission_codes_for_role(self, role_id: str) -> set[str]:
        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
        )
        return set(self.db.scalars(stmt))
