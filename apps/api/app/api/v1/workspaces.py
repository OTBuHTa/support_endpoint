from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz.deps import get_current_user, get_workspace_membership, require_permission
from app.authz.permissions import USERS_MANAGE
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import WorkspaceMembership
from app.repositories.rbac_repo import RbacRepository
from app.repositories.workspace_repo import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreateRequest, WorkspaceResponse
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=201)
def create_workspace(
    payload: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    service = WorkspaceService(db)
    workspace = service.create_workspace_for_user(user=current_user, name=payload.name)
    return WorkspaceResponse.model_validate(workspace)


@router.get("", response_model=list[WorkspaceResponse])
def list_my_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WorkspaceResponse]:
    service = WorkspaceService(db)
    workspaces = service.list_workspaces_for_user(user=current_user)
    return [WorkspaceResponse.model_validate(w) for w in workspaces]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id: str,
    membership: WorkspaceMembership = Depends(get_workspace_membership),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    # `membership` resolution already enforced object-level authorization:
    # a 404 was raised above if the caller has no membership here.
    workspace = WorkspaceRepository(db).get_by_id(workspace_id)
    return WorkspaceResponse.model_validate(workspace)


@router.get("/{workspace_id}/my-permissions")
def my_permissions(
    workspace_id: str,
    membership: WorkspaceMembership = Depends(get_workspace_membership),
    db: Session = Depends(get_db),
) -> dict:
    codes = RbacRepository(db).permission_codes_for_role(membership.role_id)
    return {"workspace_id": workspace_id, "permissions": sorted(codes)}


@router.get("/{workspace_id}/admin-only-ping")
def admin_only_ping(
    workspace_id: str,
    membership: WorkspaceMembership = Depends(require_permission(USERS_MANAGE)),
) -> dict:
    """Demonstration endpoint for the deny-by-default permission
    dependency — requires `users.manage`. Real user-management
    endpoints arrive in a later phase; this exists so Foundation ships
    a working, testable example of `require_permission`.
    """
    return {"workspace_id": workspace_id, "ok": True}
