from datetime import datetime

from pydantic import BaseModel, Field

from app.models.ticket_enums import TicketPriority, TicketStatus
from app.schemas.ticket_lookup import TagResponse


class TicketCreateRequest(BaseModel):
    client_id: str
    subject: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=20000)
    priority: TicketPriority = TicketPriority.MEDIUM
    queue_id: str | None = None
    category_id: str | None = None


class TicketUpdateRequest(BaseModel):
    subject: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20000)
    priority: TicketPriority | None = None
    queue_id: str | None = None
    category_id: str | None = None


class TicketTransitionRequest(BaseModel):
    status: TicketStatus


class TicketAssignRequest(BaseModel):
    assignee_user_id: str | None = None  # null = unassign


class TicketResponse(BaseModel):
    id: str
    client_id: str
    creator_user_id: str
    assignee_user_id: str | None
    queue_id: str | None
    category_id: str | None
    subject: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    tags: list[TagResponse] = []

    model_config = {"from_attributes": True}


class TicketListResponse(BaseModel):
    items: list[TicketResponse]
    total: int
    limit: int
    offset: int


class TicketAssignmentResponse(BaseModel):
    id: str
    ticket_id: str
    assignee_user_id: str | None
    assigned_by_user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
