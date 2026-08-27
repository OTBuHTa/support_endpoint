from datetime import timedelta

from sqlalchemy.orm import Session

from app.authz.permissions import ROLE_ADMINISTRATOR, SYSTEM_ROLE_PERMISSIONS
from app.core.config import Settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.db.base import utcnow
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.rbac_repo import RbacRepository
from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository
from app.repositories.workspace_repo import MembershipRepository, WorkspaceRepository


def ensure_system_roles(db: Session) -> dict[str, str]:
    """Idempotently ensures the four system roles and canonical
    permissions exist, returning {role_name: role_id}. Safe to call on
    every bootstrap/startup.
    """
    rbac = RbacRepository(db)
    role_ids: dict[str, str] = {}

    all_codes: set[str] = set()
    for codes in SYSTEM_ROLE_PERMISSIONS.values():
        all_codes.update(codes)

    code_to_permission_id: dict[str, str] = {}
    for code in all_codes:
        permission = rbac.get_permission_by_code(code)
        if permission is None:
            permission = rbac.create_permission(code=code)
        code_to_permission_id[code] = permission.id

    for role_name, codes in SYSTEM_ROLE_PERMISSIONS.items():
        role = rbac.get_role_by_name(role_name)
        if role is None:
            role = rbac.create_role(name=role_name, is_system=True)
        role_ids[role_name] = role.id
        for code in codes:
            rbac.grant(role_id=role.id, permission_id=code_to_permission_id[code])

    return role_ids


class AuthService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.users = UserRepository(db)
        self.workspaces = WorkspaceRepository(db)
        self.memberships = MembershipRepository(db)
        self.sessions = SessionRepository(db)
        self.audit = AuditRepository(db)

    def register_user(self, *, email: str, password: str, full_name: str = "") -> User:
        """Self-service account creation, independent of the one-time
        bootstrap flow. A freshly registered user has no workspace
        membership yet — they create or are invited into one next.
        """
        if self.users.get_by_email(email) is not None:
            raise ConflictError("An account with this email already exists")

        user = self.users.create(
            email=email, password_hash=hash_password(password), full_name=full_name
        )
        self.audit.record(
            action="auth.register",
            actor_user_id=user.id,
            resource_type="user",
            resource_id=user.id,
        )
        self.db.commit()
        return user

    def bootstrap_owner(
        self, *, email: str, password: str, full_name: str, workspace_name: str
    ) -> tuple[User, str]:
        if not self.settings.bootstrap_enabled:
            raise ConflictError("Bootstrap is disabled")
        if self.users.any_exists():
            raise ConflictError("Bootstrap has already been completed")

        role_ids = ensure_system_roles(self.db)

        user = self.users.create(
            email=email, password_hash=hash_password(password), full_name=full_name
        )
        workspace = self.workspaces.create(name=workspace_name)
        self.memberships.create(
            workspace_id=workspace.id,
            user_id=user.id,
            role_id=role_ids[ROLE_ADMINISTRATOR],
        )
        self.audit.record(
            action="auth.bootstrap",
            workspace_id=workspace.id,
            actor_user_id=user.id,
            resource_type="workspace",
            resource_id=workspace.id,
        )
        self.db.commit()
        return user, workspace.id

    def authenticate(self, *, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            self.audit.record(
                action="auth.login_failed",
                resource_type="user",
                resource_id=email,
                result="failure",
            )
            self.db.commit()
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Invalid email or password")
        return user

    def issue_token_pair(
        self, user: User, *, user_agent: str = "", ip_address: str = ""
    ) -> tuple[str, str]:
        access_token = create_access_token(subject=user.id)

        raw_refresh = generate_opaque_token()
        expires_at = utcnow() + timedelta(days=self.settings.refresh_token_days)
        self.sessions.create(
            user_id=user.id,
            token_hash=hash_opaque_token(raw_refresh),
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.audit.record(
            action="auth.login_succeeded",
            actor_user_id=user.id,
            resource_type="user",
            resource_id=user.id,
        )
        self.db.commit()
        return access_token, raw_refresh

    def refresh(self, *, raw_refresh_token: str) -> tuple[str, str]:
        token_hash = hash_opaque_token(raw_refresh_token)
        session = self.sessions.get_by_token_hash(token_hash)
        if session is None or not session.is_active:
            raise AuthenticationError("Invalid or expired refresh token")

        user = self.users.get_by_id(session.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid or expired refresh token")

        # Rotate: revoke the old session, issue a brand new one.
        self.sessions.revoke(session)
        access_token, new_refresh = self.issue_token_pair(user)
        return access_token, new_refresh

    def logout(self, *, raw_refresh_token: str) -> None:
        token_hash = hash_opaque_token(raw_refresh_token)
        session = self.sessions.get_by_token_hash(token_hash)
        if session is None:
            return
        self.sessions.revoke(session)
        self.audit.record(
            action="auth.logout",
            actor_user_id=session.user_id,
            resource_type="session",
            resource_id=session.id,
        )
        self.db.commit()
