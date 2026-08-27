from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.communication import MessageDirection
from app.models.ticket_enums import TicketPriority, TicketStatus


class PortalLinkRequest(BaseModel):
    user_email: EmailStr


class PortalLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    client_id: str
    user_id: str
    created_at: datetime


class PortalAccountResponse(BaseModel):
    link_id: str
    workspace_id: str
    workspace_name: str
    client_id: str
    client_name: str


class PortalTicketCreateRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=20_000)
    priority: TicketPriority = TicketPriority.MEDIUM


class PortalTicketResponse(BaseModel):
    id: str
    workspace_id: str
    client_id: str
    subject: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    created_at: datetime
    updated_at: datetime


class PortalMessageCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=50_000)


class PortalMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    direction: MessageDirection
    body: str
    created_at: datetime
