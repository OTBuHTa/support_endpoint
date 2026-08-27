from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.knowledge import AISuggestion, KnowledgeArticle


class KnowledgeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        workspace_id: str,
        author_user_id: str,
        title: str,
        body: str,
        status: str,
    ) -> KnowledgeArticle:
        item = KnowledgeArticle(
            workspace_id=workspace_id,
            author_user_id=author_user_id,
            title=title,
            body=body,
            status=status,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def get(self, *, workspace_id: str, article_id: str) -> KnowledgeArticle | None:
        return self.db.scalar(
            select(KnowledgeArticle).where(
                KnowledgeArticle.id == article_id,
                KnowledgeArticle.workspace_id == workspace_id,
            )
        )

    def list(self, *, workspace_id: str, published_only: bool = False) -> list[KnowledgeArticle]:
        stmt = select(KnowledgeArticle).where(KnowledgeArticle.workspace_id == workspace_id)
        if published_only:
            stmt = stmt.where(KnowledgeArticle.status == "published")
        stmt = stmt.order_by(KnowledgeArticle.updated_at.desc())
        return list(self.db.scalars(stmt))


class AISuggestionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def count_recent_for_workspace(self, *, workspace_id: str, seconds: int = 60) -> int:
        since = datetime.now(UTC) - timedelta(seconds=seconds)
        return int(
            self.db.scalar(
                select(func.count()).select_from(AISuggestion).where(
                    AISuggestion.workspace_id == workspace_id,
                    AISuggestion.created_at >= since,
                )
            )
            or 0
        )

    def create(
        self,
        *,
        workspace_id: str,
        ticket_id: str,
        actor_user_id: str,
        kind: str,
        prompt_hash: str,
        response_text: str,
    ) -> AISuggestion:
        item = AISuggestion(
            workspace_id=workspace_id,
            ticket_id=ticket_id,
            actor_user_id=actor_user_id,
            kind=kind,
            prompt_hash=prompt_hash,
            response_text=response_text,
        )
        self.db.add(item)
        self.db.flush()
        return item
