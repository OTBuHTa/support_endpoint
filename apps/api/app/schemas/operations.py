from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.operations import NotificationType, TaskStatus
from app.models.ticket_enums import TicketPriority


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=20_000)
    assignee_user_id: str | None = None
    due_at: datetime | None = None


class TaskStatusRequest(BaseModel):
    status: TaskStatus


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    creator_user_id: str
    assignee_user_id: str | None
    title: str
    description: str
    status: TaskStatus
    due_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SLAPolicyUpsertRequest(BaseModel):
    priority: TicketPriority
    first_response_minutes: int = Field(ge=1, le=43_200)
    resolution_minutes: int = Field(ge=1, le=525_600)
    warning_minutes_before: int = Field(default=15, ge=0, le=10_080)


class SLAPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    priority: TicketPriority
    first_response_minutes: int
    resolution_minutes: int
    warning_minutes_before: int
    is_active: bool


class TicketSLAResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: str
    policy_id: str
    first_response_due_at: datetime
    resolution_due_at: datetime
    first_response_at: datetime | None
    resolved_at: datetime | None
    first_response_breached: bool
    resolution_breached: bool


class SLAEvaluationResponse(BaseModel):
    evaluated: int
    warnings_created: int
    breaches_created: int


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str | None
    type: NotificationType
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime
