from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz.deps import require_permission
from app.authz.permissions import (
    TICKETS_ASSIGN,
    TICKETS_CLOSE,
    TICKETS_CREATE,
    TICKETS_READ,
    TICKETS_UPDATE,
)
from app.core.exceptions import AuthorizationError
from app.db.session import get_db
from app.models.ticket import Ticket
from app.models.ticket_enums import TicketPriority, TicketStatus
from app.models.workspace import WorkspaceMembership
from app.repositories.rbac_repo import RbacRepository
from app.schemas.ticket import (
    TicketAssignmentResponse,
    TicketAssignRequest,
    TicketCreateRequest,
    TicketListResponse,
    TicketResponse,
    TicketTransitionRequest,
    TicketUpdateRequest,
)
from app.schemas.ticket_lookup import TagResponse
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/workspaces/{workspace_id}/tickets", tags=["tickets"])


def _to_response(ticket: Ticket) -> TicketResponse:
    """Manual serialization for the tags relationship: `ticket.tags` is
    a list of `TicketTag` join rows, not `Tag` rows, so a single
    `from_attributes` validation of the ORM object can't bridge that.
    Build a plain dict instead, transforming tags explicitly.
    """
    return TicketResponse.model_validate(
        {
            "id": ticket.id,
            "client_id": ticket.client_id,
            "creator_user_id": ticket.creator_user_id,
            "assignee_user_id": ticket.assignee_user_id,
            "queue_id": ticket.queue_id,
            "category_id": ticket.category_id,
            "subject": ticket.subject,
            "description": ticket.description,
            "status": ticket.status,
            "priority": ticket.priority,
            "tags": [TagResponse.model_validate(tt.tag) for tt in ticket.tags],
        }
    )


@router.post("", response_model=TicketResponse, status_code=201)
def create_ticket(
    workspace_id: str,
    payload: TicketCreateRequest,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_CREATE)),
    db: Session = Depends(get_db),
) -> TicketResponse:
    service = TicketService(db)
    ticket = service.create(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        client_id=payload.client_id,
        subject=payload.subject,
        description=payload.description,
        priority=payload.priority,
        queue_id=payload.queue_id,
        category_id=payload.category_id,
    )
    return _to_response(ticket)


@router.get("", response_model=TicketListResponse)
def list_tickets(
    workspace_id: str,
    q: str = "",
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    queue_id: str | None = None,
    category_id: str | None = None,
    assignee_user_id: str | None = None,
    client_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_READ)),
    db: Session = Depends(get_db),
) -> TicketListResponse:
    service = TicketService(db)
    items, total = service.list(
        workspace_id=workspace_id,
        q=q,
        status=status,
        priority=priority,
        queue_id=queue_id,
        category_id=category_id,
        assignee_user_id=assignee_user_id,
        client_id=client_id,
        limit=limit,
        offset=offset,
    )
    return TicketListResponse(
        items=[_to_response(t) for t in items], total=total, limit=limit, offset=offset
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    workspace_id: str,
    ticket_id: str,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_READ)),
    db: Session = Depends(get_db),
) -> TicketResponse:
    service = TicketService(db)
    return _to_response(service.get(workspace_id=workspace_id, ticket_id=ticket_id))


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    workspace_id: str,
    ticket_id: str,
    payload: TicketUpdateRequest,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_UPDATE)),
    db: Session = Depends(get_db),
) -> TicketResponse:
    service = TicketService(db)
    ticket = service.update(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        ticket_id=ticket_id,
        subject=payload.subject,
        description=payload.description,
        priority=payload.priority,
        queue_id=payload.queue_id,
        category_id=payload.category_id,
    )
    return _to_response(ticket)


@router.post("/{ticket_id}/transition", response_model=TicketResponse)
def transition_ticket(
    workspace_id: str,
    ticket_id: str,
    payload: TicketTransitionRequest,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_UPDATE)),
    db: Session = Depends(get_db),
) -> TicketResponse:
    """`tickets.update` is enough for most transitions; moving a
    ticket to CLOSED additionally requires `tickets.close` (see
    app/authz/permissions.py — Operator has update but not close).
    """
    if payload.status == TicketStatus.CLOSED:
        caller_permissions = RbacRepository(db).permission_codes_for_role(membership.role_id)
        if TICKETS_CLOSE not in caller_permissions:
            raise AuthorizationError("Closing a ticket requires the tickets.close permission")

    service = TicketService(db)
    ticket = service.transition_status(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        ticket_id=ticket_id,
        target_status=payload.status,
    )
    return _to_response(ticket)


@router.post("/{ticket_id}/assign", response_model=TicketResponse)
def assign_ticket(
    workspace_id: str,
    ticket_id: str,
    payload: TicketAssignRequest,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_ASSIGN)),
    db: Session = Depends(get_db),
) -> TicketResponse:
    service = TicketService(db)
    ticket = service.assign(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        ticket_id=ticket_id,
        assignee_user_id=payload.assignee_user_id,
    )
    return _to_response(ticket)


@router.get("/{ticket_id}/assignments", response_model=list[TicketAssignmentResponse])
def list_assignment_history(
    workspace_id: str,
    ticket_id: str,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_READ)),
    db: Session = Depends(get_db),
) -> list[TicketAssignmentResponse]:
    service = TicketService(db)
    history = service.assignment_history(workspace_id=workspace_id, ticket_id=ticket_id)
    return [TicketAssignmentResponse.model_validate(h) for h in history]


@router.post("/{ticket_id}/tags/{tag_id}", response_model=TicketResponse, status_code=201)
def add_tag(
    workspace_id: str,
    ticket_id: str,
    tag_id: str,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_UPDATE)),
    db: Session = Depends(get_db),
) -> TicketResponse:
    service = TicketService(db)
    ticket = service.add_tag(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        ticket_id=ticket_id,
        tag_id=tag_id,
    )
    return _to_response(ticket)


@router.delete("/{ticket_id}/tags/{tag_id}", response_model=TicketResponse)
def remove_tag(
    workspace_id: str,
    ticket_id: str,
    tag_id: str,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_UPDATE)),
    db: Session = Depends(get_db),
) -> TicketResponse:
    service = TicketService(db)
    ticket = service.remove_tag(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        ticket_id=ticket_id,
        tag_id=tag_id,
    )
    return _to_response(ticket)
