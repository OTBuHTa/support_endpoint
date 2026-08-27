from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz.deps import require_permission
from app.authz.permissions import AI_ASSIST, KNOWLEDGE_READ, KNOWLEDGE_WRITE
from app.db.session import get_db
from app.models.workspace import WorkspaceMembership
from app.schemas.knowledge import (
    AIAssistRequest,
    AISuggestionResponse,
    KnowledgeArticleCreateRequest,
    KnowledgeArticleResponse,
)
from app.services.knowledge_service import AIAssistService, KnowledgeService

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["knowledge-ai"])


@router.post("/knowledge", response_model=KnowledgeArticleResponse, status_code=201)
def create_article(
    workspace_id: str,
    payload: KnowledgeArticleCreateRequest,
    membership: WorkspaceMembership = Depends(require_permission(KNOWLEDGE_WRITE)),
    db: Session = Depends(get_db),
) -> KnowledgeArticleResponse:
    item = KnowledgeService(db).create(
        workspace_id=workspace_id,
        actor_user_id=membership.user_id,
        title=payload.title,
        body=payload.body,
        status=payload.status,
    )
    return KnowledgeArticleResponse.model_validate(item)


@router.get("/knowledge", response_model=list[KnowledgeArticleResponse])
def list_articles(
    workspace_id: str,
    membership: WorkspaceMembership = Depends(require_permission(KNOWLEDGE_READ)),
    db: Session = Depends(get_db),
) -> list[KnowledgeArticleResponse]:
    items = KnowledgeService(db).list(workspace_id=workspace_id)
    return [KnowledgeArticleResponse.model_validate(item) for item in items]


@router.get("/knowledge/{article_id}", response_model=KnowledgeArticleResponse)
def get_article(
    workspace_id: str,
    article_id: str,
    membership: WorkspaceMembership = Depends(require_permission(KNOWLEDGE_READ)),
    db: Session = Depends(get_db),
) -> KnowledgeArticleResponse:
    item = KnowledgeService(db).get(workspace_id=workspace_id, article_id=article_id)
    return KnowledgeArticleResponse.model_validate(item)


@router.post("/tickets/{ticket_id}/ai/suggestions", response_model=AISuggestionResponse, status_code=201)
def create_ai_suggestion(
    workspace_id: str,
    ticket_id: str,
    payload: AIAssistRequest,
    membership: WorkspaceMembership = Depends(require_permission(AI_ASSIST)),
    db: Session = Depends(get_db),
) -> AISuggestionResponse:
    item = AIAssistService(db).suggest(
        workspace_id=workspace_id,
        ticket_id=ticket_id,
        actor_user_id=membership.user_id,
        kind=payload.kind,
    )
    return AISuggestionResponse.model_validate(item)
