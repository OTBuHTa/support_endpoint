from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz.deps import require_permission
from app.authz.permissions import SETTINGS_MANAGE, TICKETS_READ
from app.db.session import get_db
from app.models.workspace import WorkspaceMembership
from app.schemas.ticket_lookup import QueueCreateRequest, QueueResponse, QueueUpdateRequest
from app.services.ticket_lookup_service import QueueService

router = APIRouter(prefix="/workspaces/{workspace_id}/queues", tags=["queues"])


@router.post("", response_model=QueueResponse, status_code=201)
def create_queue(
    workspace_id: str,
    payload: QueueCreateRequest,
    membership: WorkspaceMembership = Depends(require_permission(SETTINGS_MANAGE)),
    db: Session = Depends(get_db),
) -> QueueResponse:
    service = QueueService(db)
    queue = service.create(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        name=payload.name,
        description=payload.description,
    )
    return QueueResponse.model_validate(queue)


@router.get("", response_model=list[QueueResponse])
def list_queues(
    workspace_id: str,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_READ)),
    db: Session = Depends(get_db),
) -> list[QueueResponse]:
    service = QueueService(db)
    return [QueueResponse.model_validate(q) for q in service.list_all(workspace_id=workspace_id)]


@router.get("/{queue_id}", response_model=QueueResponse)
def get_queue(
    workspace_id: str,
    queue_id: str,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_READ)),
    db: Session = Depends(get_db),
) -> QueueResponse:
    service = QueueService(db)
    return QueueResponse.model_validate(service.get(workspace_id=workspace_id, queue_id=queue_id))


@router.patch("/{queue_id}", response_model=QueueResponse)
def update_queue(
    workspace_id: str,
    queue_id: str,
    payload: QueueUpdateRequest,
    membership: WorkspaceMembership = Depends(require_permission(SETTINGS_MANAGE)),
    db: Session = Depends(get_db),
) -> QueueResponse:
    service = QueueService(db)
    queue = service.update(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        queue_id=queue_id,
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
    )
    return QueueResponse.model_validate(queue)
