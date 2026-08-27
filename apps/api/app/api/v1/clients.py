from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz.deps import require_permission
from app.authz.permissions import CLIENTS_READ, CLIENTS_WRITE
from app.db.session import get_db
from app.models.workspace import WorkspaceMembership
from app.schemas.client import (
    ClientContactCreateRequest,
    ClientContactResponse,
    ClientCreateRequest,
    ClientListResponse,
    ClientResponse,
    ClientUpdateRequest,
)
from app.services.client_service import ClientService

router = APIRouter(prefix="/workspaces/{workspace_id}/clients", tags=["clients"])


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(
    workspace_id: str,
    payload: ClientCreateRequest,
    membership: WorkspaceMembership = Depends(require_permission(CLIENTS_WRITE)),
    db: Session = Depends(get_db),
) -> ClientResponse:
    service = ClientService(db)
    client = service.create(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        full_name=payload.full_name,
        primary_email=payload.primary_email,
        primary_phone=payload.primary_phone,
        organization_id=payload.organization_id,
        notes=payload.notes,
    )
    return ClientResponse.model_validate(client)


@router.get("", response_model=ClientListResponse)
def list_clients(
    workspace_id: str,
    q: str = "",
    organization_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
    membership: WorkspaceMembership = Depends(require_permission(CLIENTS_READ)),
    db: Session = Depends(get_db),
) -> ClientListResponse:
    service = ClientService(db)
    items, total = service.list_clients(
        workspace_id=workspace_id,
        q=q,
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )
    return ClientListResponse(
        items=[ClientResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    workspace_id: str,
    client_id: str,
    membership: WorkspaceMembership = Depends(require_permission(CLIENTS_READ)),
    db: Session = Depends(get_db),
) -> ClientResponse:
    service = ClientService(db)
    client = service.get(workspace_id=workspace_id, client_id=client_id)
    return ClientResponse.model_validate(client)


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    workspace_id: str,
    client_id: str,
    payload: ClientUpdateRequest,
    membership: WorkspaceMembership = Depends(require_permission(CLIENTS_WRITE)),
    db: Session = Depends(get_db),
) -> ClientResponse:
    service = ClientService(db)
    client = service.update(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        client_id=client_id,
        full_name=payload.full_name,
        primary_email=payload.primary_email,
        primary_phone=payload.primary_phone,
        organization_id=payload.organization_id,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}", status_code=204)
def deactivate_client(
    workspace_id: str,
    client_id: str,
    membership: WorkspaceMembership = Depends(require_permission(CLIENTS_WRITE)),
    db: Session = Depends(get_db),
) -> None:
    """Soft-delete: customer records are deactivated, never hard-deleted,
    so ticket history (Phase 4+) never dangles on a missing client.
    """
    service = ClientService(db)
    service.update(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        client_id=client_id,
        is_active=False,
    )


@router.post("/{client_id}/contacts", response_model=ClientContactResponse, status_code=201)
def add_contact(
    workspace_id: str,
    client_id: str,
    payload: ClientContactCreateRequest,
    membership: WorkspaceMembership = Depends(require_permission(CLIENTS_WRITE)),
    db: Session = Depends(get_db),
) -> ClientContactResponse:
    service = ClientService(db)
    contact = service.add_contact(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        client_id=client_id,
        label=payload.label,
        channel_type=payload.channel_type,
        value=payload.value,
    )
    return ClientContactResponse.model_validate(contact)


@router.get("/{client_id}/contacts", response_model=list[ClientContactResponse])
def list_contacts(
    workspace_id: str,
    client_id: str,
    membership: WorkspaceMembership = Depends(require_permission(CLIENTS_READ)),
    db: Session = Depends(get_db),
) -> list[ClientContactResponse]:
    service = ClientService(db)
    contacts = service.list_contacts(workspace_id=workspace_id, client_id=client_id)
    return [ClientContactResponse.model_validate(c) for c in contacts]


@router.delete("/{client_id}/contacts/{contact_id}", status_code=204)
def delete_contact(
    workspace_id: str,
    client_id: str,
    contact_id: str,
    membership: WorkspaceMembership = Depends(require_permission(CLIENTS_WRITE)),
    db: Session = Depends(get_db),
) -> None:
    service = ClientService(db)
    service.delete_contact(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        client_id=client_id,
        contact_id=contact_id,
    )
