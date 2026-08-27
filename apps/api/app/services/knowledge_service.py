import hashlib

from sqlalchemy.orm import Session

from app.ai.gateway import LLMGateway
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.knowledge import AISuggestion, KnowledgeArticle
from app.repositories.audit_repo import AuditRepository
from app.repositories.knowledge_repo import AISuggestionRepository, KnowledgeRepository
from app.repositories.ticket_repo import TicketRepository

_ALLOWED_STATUSES = {"draft", "published", "archived"}
_ALLOWED_KINDS = {"reply", "summary", "next_steps"}


class KnowledgeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = KnowledgeRepository(db)
        self.audit = AuditRepository(db)

    def create(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        title: str,
        body: str,
        status: str,
    ) -> KnowledgeArticle:
        if status not in _ALLOWED_STATUSES:
            raise ValidationAppError("invalid knowledge article status")
        item = self.repo.create(
            workspace_id=workspace_id,
            author_user_id=actor_user_id,
            title=title,
            body=body,
            status=status,
        )
        self.audit.record(
            action="knowledge.article.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="knowledge_article",
            resource_id=item.id,
            metadata={"status": status},
        )
        self.db.commit()
        return item

    def get(self, *, workspace_id: str, article_id: str) -> KnowledgeArticle:
        item = self.repo.get(workspace_id=workspace_id, article_id=article_id)
        if item is None:
            raise NotFoundError("Knowledge article not found")
        return item

    def list(self, *, workspace_id: str) -> list[KnowledgeArticle]:
        return self.repo.list(workspace_id=workspace_id)


class AIAssistService:
    def __init__(self, db: Session, gateway: LLMGateway | None = None) -> None:
        self.db = db
        self.tickets = TicketRepository(db)
        self.knowledge = KnowledgeRepository(db)
        self.suggestions = AISuggestionRepository(db)
        self.audit = AuditRepository(db)
        self.gateway = gateway or LLMGateway()
        self.settings = get_settings()

    def suggest(
        self,
        *,
        workspace_id: str,
        ticket_id: str,
        actor_user_id: str,
        kind: str,
    ) -> AISuggestion:
        if kind not in _ALLOWED_KINDS:
            raise ValidationAppError("invalid AI suggestion kind")
        ticket = self.tickets.get_in_workspace(workspace_id=workspace_id, ticket_id=ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found")

        recent = self.suggestions.count_recent_for_workspace(workspace_id=workspace_id)
        if recent >= self.settings.llm_workspace_requests_per_minute:
            raise ValidationAppError("AI workspace rate limit exceeded")

        articles = self.knowledge.list(workspace_id=workspace_id, published_only=True)[:5]
        kb_context = "\n\n".join(f"# {a.title}\n{a.body[:3000]}" for a in articles)
        prompt = (
            f"Task: {kind}\n"
            f"Ticket subject: {ticket.subject}\n"
            f"Ticket description: {ticket.description}\n"
            f"Knowledge base:\n{kb_context or '[no published articles]'}"
        )
        system_prompt = (
            "You are an advisory customer-support assistant. Return a concise proposal only. "
            "Do not claim to have sent messages, changed ticket state, changed permissions, "
            "executed commands, or modified infrastructure."
        )
        try:
            result = self.gateway.suggest(system_prompt=system_prompt, user_prompt=prompt)
        except Exception as exc:
            raise ValidationAppError("AI assistance is unavailable") from exc

        item = self.suggestions.create(
            workspace_id=workspace_id,
            ticket_id=ticket_id,
            actor_user_id=actor_user_id,
            kind=kind,
            prompt_hash=hashlib.sha256(result.redacted_prompt.encode()).hexdigest(),
            response_text=result.text,
        )
        self.audit.record(
            action="ai.suggestion.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="ai_suggestion",
            resource_id=item.id,
            metadata={"ticket_id": ticket_id, "kind": kind},
        )
        self.db.commit()
        return item
