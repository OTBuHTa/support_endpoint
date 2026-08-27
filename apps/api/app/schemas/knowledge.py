from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeArticleCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=200_000)
    status: str = Field(default="draft", max_length=16)


class KnowledgeArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author_user_id: str
    title: str
    body: str
    status: str
    created_at: datetime
    updated_at: datetime


class AIAssistRequest(BaseModel):
    kind: str = Field(default="reply", max_length=32)


class AISuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    actor_user_id: str
    kind: str
    response_text: str
    created_at: datetime
