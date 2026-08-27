from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz.deps import require_permission
from app.authz.permissions import (
    NOTIFICATIONS_READ,
    SLA_MANAGE,
    SLA_READ,
    TASKS_READ,
    TASKS_WRITE,
)
from app.db.session import get_db
from app.models.workspace import WorkspaceMembership
from app.schemas.operations import (
    NotificationResponse,
    SLAEvaluationResponse,
    SLAPolicyResponse,
    SLAPolicyUpsertRequest,
    TaskCreateRequest,
    TaskResponse,
    TaskStatusRequest,
    TicketSLAResponse,
)
from app.services.operations_service import OperationsService

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["operations"])


@router.post("/tickets/{ticket_id}/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    workspace_id: str,
    ticket_id: str,
    payload: TaskCreateRequest,
    membership: WorkspaceMembership = Depends(require_permission(TASKS_WRITE)),
    db: Session = Depends(get_db),
) -> TaskResponse:
    item = OperationsService(db).create_task(
        workspace_id=workspace_id,
        ticket_id=ticket_id,
        actor_user_id=membership.user_id,
        title=payload.title,
        description=payload.description,
        assignee_user_id=payload.assignee_user_id,
        due_at=payload.due_at,
    )
    return TaskResponse.model_validate(item)


@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    workspace_id: str,
    ticket_id: str | None = None,
    membership: WorkspaceMembership = Depends(require_permission(TASKS_READ)),
    db: Session = Depends(get_db),
) -> list[TaskResponse]:
    items = OperationsService(db).list_tasks(workspace_id=workspace_id, ticket_id=ticket_id)
    return [TaskResponse.model_validate(item) for item in items]


@router.post("/tasks/{task_id}/status", response_model=TaskResponse)
def set_task_status(
    workspace_id: str,
    task_id: str,
    payload: TaskStatusRequest,
    membership: WorkspaceMembership = Depends(require_permission(TASKS_WRITE)),
    db: Session = Depends(get_db),
) -> TaskResponse:
    item = OperationsService(db).set_task_status(
        workspace_id=workspace_id,
        task_id=task_id,
        actor_user_id=membership.user_id,
        status=payload.status,
    )
    return TaskResponse.model_validate(item)


@router.get("/sla/policies", response_model=list[SLAPolicyResponse])
def list_sla_policies(
    workspace_id: str,
    membership: WorkspaceMembership = Depends(require_permission(SLA_READ)),
    db: Session = Depends(get_db),
) -> list[SLAPolicyResponse]:
    items = OperationsService(db).list_policies(workspace_id=workspace_id)
    return [SLAPolicyResponse.model_validate(item) for item in items]


@router.put("/sla/policies", response_model=SLAPolicyResponse)
def upsert_sla_policy(
    workspace_id: str,
    payload: SLAPolicyUpsertRequest,
    membership: WorkspaceMembership = Depends(require_permission(SLA_MANAGE)),
    db: Session = Depends(get_db),
) -> SLAPolicyResponse:
    item = OperationsService(db).upsert_policy(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        priority=payload.priority,
        first_response_minutes=payload.first_response_minutes,
        resolution_minutes=payload.resolution_minutes,
        warning_minutes_before=payload.warning_minutes_before,
    )
    return SLAPolicyResponse.model_validate(item)


@router.get("/tickets/{ticket_id}/sla", response_model=TicketSLAResponse)
def get_ticket_sla(
    workspace_id: str,
    ticket_id: str,
    membership: WorkspaceMembership = Depends(require_permission(SLA_READ)),
    db: Session = Depends(get_db),
) -> TicketSLAResponse:
    item = OperationsService(db).get_ticket_sla(workspace_id=workspace_id, ticket_id=ticket_id)
    return TicketSLAResponse.model_validate(item)


@router.post("/sla/evaluate", response_model=SLAEvaluationResponse)
def evaluate_sla(
    workspace_id: str,
    membership: WorkspaceMembership = Depends(require_permission(SLA_MANAGE)),
    db: Session = Depends(get_db),
) -> SLAEvaluationResponse:
    evaluated, warnings, breaches = OperationsService(db).evaluate_sla(workspace_id=workspace_id)
    return SLAEvaluationResponse(
        evaluated=evaluated,
        warnings_created=warnings,
        breaches_created=breaches,
    )


@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(
    workspace_id: str,
    membership: WorkspaceMembership = Depends(require_permission(NOTIFICATIONS_READ)),
    db: Session = Depends(get_db),
) -> list[NotificationResponse]:
    items = OperationsService(db).list_notifications(
        workspace_id=workspace_id, user_id=membership.user_id
    )
    return [NotificationResponse.model_validate(item) for item in items]


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    workspace_id: str,
    notification_id: str,
    membership: WorkspaceMembership = Depends(require_permission(NOTIFICATIONS_READ)),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    item = OperationsService(db).mark_notification_read(
        workspace_id=workspace_id,
        user_id=membership.user_id,
        notification_id=notification_id,
    )
    return NotificationResponse.model_validate(item)
