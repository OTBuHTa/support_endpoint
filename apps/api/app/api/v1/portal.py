from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz.deps import get_current_user, require_permission
from app.authz.permissions import CLIENTS_WRITE
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import WorkspaceMembership
from app.schemas.portal import (
    PortalAccountResponse,
    PortalLinkRequest,
    PortalLinkResponse,
    PortalMessageCreateRequest,
    PortalMessageResponse,
    PortalTicketCreateRequest,
    PortalTicketResponse,
)
from app.services.portal_service import PortalService

router = APIRouter(tags=["portal"])


def _ticket_response(ticket) -> PortalTicketResponse:
    return PortalTicketResponse(
        id=ticket.id,
        workspace_id=ticket.workspace_id,
        client_id=ticket.client_id,
        subject=ticket.subject,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.post(
    "/workspaces/{workspace_id}/clients/{client_id}/portal-link",
    response_model=PortalLinkResponse,
    status_code=201,
)
def link_client_user(
    workspace_id: str,
    client_id: str,
    payload: PortalLinkRequest,
    membership: WorkspaceMembership = Depends(require_permission(CLIENTS_WRITE)),
    db: Session = Depends(get_db),
) -> PortalLinkResponse:
    item = PortalService(db).link_client_user(
        workspace_id=workspace_id,
        client_id=client_id,
        user_email=str(payload.user_email),
        actor_user_id=membership.user_id,
    )
    return PortalLinkResponse.model_validate(item)


@router.get("/portal/accounts", response_model=list[PortalAccountResponse])
def portal_accounts(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[PortalAccountResponse]:
    items = PortalService(db).accounts(user_id=current_user.id)
    return [PortalAccountResponse(**item) for item in items]


@router.get("/portal/accounts/{link_id}/tickets", response_model=list[PortalTicketResponse])
def portal_tickets(
    link_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PortalTicketResponse]:
    items = PortalService(db).list_tickets(user_id=current_user.id, link_id=link_id)
    return [_ticket_response(item) for item in items]


@router.post(
    "/portal/accounts/{link_id}/tickets", response_model=PortalTicketResponse, status_code=201
)
def portal_create_ticket(
    link_id: str,
    payload: PortalTicketCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortalTicketResponse:
    item = PortalService(db).create_ticket(
        user_id=current_user.id,
        link_id=link_id,
        subject=payload.subject,
        description=payload.description,
        priority=payload.priority,
    )
    return _ticket_response(item)


@router.get(
    "/portal/accounts/{link_id}/tickets/{ticket_id}", response_model=PortalTicketResponse
)
def portal_ticket(
    link_id: str,
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortalTicketResponse:
    item = PortalService(db).get_ticket(
        user_id=current_user.id, link_id=link_id, ticket_id=ticket_id
    )
    return _ticket_response(item)


@router.get(
    "/portal/accounts/{link_id}/tickets/{ticket_id}/messages",
    response_model=list[PortalMessageResponse],
)
def portal_messages(
    link_id: str,
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PortalMessageResponse]:
    items = PortalService(db).list_messages(
        user_id=current_user.id, link_id=link_id, ticket_id=ticket_id
    )
    return [PortalMessageResponse.model_validate(item) for item in items]


@router.post(
    "/portal/accounts/{link_id}/tickets/{ticket_id}/messages",
    response_model=PortalMessageResponse,
    status_code=201,
)
def portal_add_message(
    link_id: str,
    ticket_id: str,
    payload: PortalMessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortalMessageResponse:
    item = PortalService(db).add_message(
        user_id=current_user.id,
        link_id=link_id,
        ticket_id=ticket_id,
        body=payload.body,
    )
    return PortalMessageResponse.model_validate(item)
