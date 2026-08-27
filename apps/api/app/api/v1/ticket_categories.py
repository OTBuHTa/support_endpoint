from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz.deps import require_permission
from app.authz.permissions import SETTINGS_MANAGE, TICKETS_READ
from app.db.session import get_db
from app.models.workspace import WorkspaceMembership
from app.schemas.ticket_lookup import (
    TicketCategoryCreateRequest,
    TicketCategoryResponse,
    TicketCategoryUpdateRequest,
)
from app.services.ticket_lookup_service import TicketCategoryService

router = APIRouter(
    prefix="/workspaces/{workspace_id}/ticket-categories", tags=["ticket-categories"]
)


@router.post("", response_model=TicketCategoryResponse, status_code=201)
def create_category(
    workspace_id: str,
    payload: TicketCategoryCreateRequest,
    membership: WorkspaceMembership = Depends(require_permission(SETTINGS_MANAGE)),
    db: Session = Depends(get_db),
) -> TicketCategoryResponse:
    service = TicketCategoryService(db)
    category = service.create(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        name=payload.name,
        description=payload.description,
    )
    return TicketCategoryResponse.model_validate(category)


@router.get("", response_model=list[TicketCategoryResponse])
def list_categories(
    workspace_id: str,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_READ)),
    db: Session = Depends(get_db),
) -> list[TicketCategoryResponse]:
    service = TicketCategoryService(db)
    return [
        TicketCategoryResponse.model_validate(c)
        for c in service.list_all(workspace_id=workspace_id)
    ]


@router.get("/{category_id}", response_model=TicketCategoryResponse)
def get_category(
    workspace_id: str,
    category_id: str,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_READ)),
    db: Session = Depends(get_db),
) -> TicketCategoryResponse:
    service = TicketCategoryService(db)
    category = service.get(workspace_id=workspace_id, category_id=category_id)
    return TicketCategoryResponse.model_validate(category)


@router.patch("/{category_id}", response_model=TicketCategoryResponse)
def update_category(
    workspace_id: str,
    category_id: str,
    payload: TicketCategoryUpdateRequest,
    membership: WorkspaceMembership = Depends(require_permission(SETTINGS_MANAGE)),
    db: Session = Depends(get_db),
) -> TicketCategoryResponse:
    service = TicketCategoryService(db)
    category = service.update(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        category_id=category_id,
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
    )
    return TicketCategoryResponse.model_validate(category)
