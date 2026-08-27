from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz.deps import require_permission
from app.authz.permissions import SETTINGS_MANAGE, TICKETS_READ
from app.db.session import get_db
from app.models.workspace import WorkspaceMembership
from app.schemas.ticket_lookup import TagCreateRequest, TagResponse
from app.services.ticket_lookup_service import TagService

router = APIRouter(prefix="/workspaces/{workspace_id}/tags", tags=["tags"])


@router.post("", response_model=TagResponse, status_code=201)
def create_tag(
    workspace_id: str,
    payload: TagCreateRequest,
    membership: WorkspaceMembership = Depends(require_permission(SETTINGS_MANAGE)),
    db: Session = Depends(get_db),
) -> TagResponse:
    service = TagService(db)
    tag = service.create(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        name=payload.name,
        color=payload.color,
    )
    return TagResponse.model_validate(tag)


@router.get("", response_model=list[TagResponse])
def list_tags(
    workspace_id: str,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_READ)),
    db: Session = Depends(get_db),
) -> list[TagResponse]:
    service = TagService(db)
    return [TagResponse.model_validate(t) for t in service.list_all(workspace_id=workspace_id)]
