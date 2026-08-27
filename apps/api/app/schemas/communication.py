from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.communication import ConversationChannel, MessageDirection


class ConversationCreateRequest(BaseModel):
    channel: ConversationChannel
    subject: str = Field(default="", max_length=255)
    external_thread_ref: str | None = Field(default=None, max_length=255)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    created_by_user_id: str
    channel: ConversationChannel
    subject: str
    external_thread_ref: str | None
    created_at: datetime
    updated_at: datetime


class MessageCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=100_000)


class InboundMessageCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=100_000)
    external_message_ref: str | None = Field(default=None, max_length=255)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    author_user_id: str | None
    direction: MessageDirection
    body: str
    external_message_ref: str | None
    created_at: datetime
    updated_at: datetime


class InternalNoteCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=100_000)


class InternalNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    author_user_id: str
    body: str
    created_at: datetime
    updated_at: datetime


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    message_id: str | None
    internal_note_id: str | None
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: datetime
