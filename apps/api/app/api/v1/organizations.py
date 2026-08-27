from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz.deps import require_permission
from app.authz.permissions import CLIENTS_READ, CLIENTS_WRITE
from app.db.session import get_db
from app.models.workspace import WorkspaceMembership
from app.schemas.client import (
    ClientOrganizationCreateRequest,
    ClientOrganizationListResponse,
    ClientOrganizationResponse,
    ClientOrganizationUpdateRequest,
)
from app.services.client_service import ClientOrganizationService

router = APIRouter(prefix="/workspaces/{workspace_id}/organizations", tags=["organizations"])


@router.post("", response_model=ClientOrganizationResponse, status_code=201)
def create_organization(
    workspace_id: str,
    payload: ClientOrganizationCreateRequest,
    membership: WorkspaceMembership = Depends(require_permission(CLIENTS_WRITE)),
    db: Session = Depends(get_db),
) -> ClientOrganizationResponse:
    service = ClientOrganizationService(db)
    org = service.create(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        name=payload.name,
        domain=payload.domain,
        notes=payload.notes,
    )
    return ClientOrganizationResponse.model_validate(org)


@router.get("", response_model=ClientOrganizationListResponse)
def list_organizations(
    workspace_id: str,
    q: str = "",
    limit: int = 20,
    offset: int = 0,
    membership: WorkspaceMembership = Depends(require_permission(CLIENTS_READ)),
    db: Session = Depends(get_db),
) -> ClientOrganizationListResponse:
    service = ClientOrganizationService(db)
    items, total = service.list_organizations(
        workspace_id=workspace_id, q=q, limit=limit, offset=offset
    )
    return ClientOrganizationListResponse(
        items=[ClientOrganizationResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{org_id}", response_model=ClientOrganizationResponse)
def get_organization(
    workspace_id: str,
    org_id: str,
    membership: WorkspaceMembership = Depends(require_permission(CLIENTS_READ)),
    db: Session = Depends(get_db),
) -> ClientOrganizationResponse:
    service = ClientOrganizationService(db)
    org = service.get(workspace_id=workspace_id, org_id=org_id)
    return ClientOrganizationResponse.model_validate(org)


@router.patch("/{org_id}", response_model=ClientOrganizationResponse)
def update_organization(
    workspace_id: str,
    org_id: str,
    payload: ClientOrganizationUpdateRequest,
    membership: WorkspaceMembership = Depends(require_permission(CLIENTS_WRITE)),
    db: Session = Depends(get_db),
) -> ClientOrganizationResponse:
    service = ClientOrganizationService(db)
    org = service.update(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        org_id=org_id,
        name=payload.name,
        domain=payload.domain,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    return ClientOrganizationResponse.model_validate(org)
