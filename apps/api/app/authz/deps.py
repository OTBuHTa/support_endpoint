import jwt
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import WorkspaceMembership
from app.repositories.rbac_repo import RbacRepository
from app.repositories.user_repo import UserRepository
from app.repositories.workspace_repo import MembershipRepository


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("Missing or malformed Authorization header")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired access token") from exc

    if payload.get("type") != "access":
        raise AuthenticationError("Wrong token type")

    user = UserRepository(db).get_by_id(payload["sub"])
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    return user


def get_workspace_membership(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceMembership:
    """Object-level authorization primitive: resolves the caller's
    membership for the requested workspace. Deliberately raises 404
    (not 403) on a missing membership so that the existence of a
    workspace the caller does not belong to is never disclosed — this
    is the core cross-workspace IDOR/BOLA guard.
    """
    membership = MembershipRepository(db).get(workspace_id=workspace_id, user_id=current_user.id)
    if membership is None:
        raise NotFoundError("Workspace not found")
    return membership


def require_permission(permission_code: str):
    """Dependency factory: deny-by-default check that the caller's
    role in the target workspace carries the given permission code.
    """

    def _dependency(
        membership: WorkspaceMembership = Depends(get_workspace_membership),
        db: Session = Depends(get_db),
    ) -> WorkspaceMembership:
        codes = RbacRepository(db).permission_codes_for_role(membership.role_id)
        if permission_code not in codes:
            raise NotFoundError("Workspace not found")
        return membership

    return _dependency
