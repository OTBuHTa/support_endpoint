from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ticket import Queue, Tag, TicketCategory


class QueueRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, workspace_id: str, name: str, description: str = "") -> Queue:
        queue = Queue(workspace_id=workspace_id, name=name, description=description)
        self.db.add(queue)
        self.db.flush()
        return queue

    def get_in_workspace(self, *, workspace_id: str, queue_id: str) -> Queue | None:
        stmt = select(Queue).where(Queue.id == queue_id, Queue.workspace_id == workspace_id)
        return self.db.scalar(stmt)

    def list_in_workspace(self, *, workspace_id: str) -> list[Queue]:
        stmt = select(Queue).where(Queue.workspace_id == workspace_id).order_by(Queue.name)
        return list(self.db.scalars(stmt))


class TicketCategoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, workspace_id: str, name: str, description: str = "") -> TicketCategory:
        category = TicketCategory(workspace_id=workspace_id, name=name, description=description)
        self.db.add(category)
        self.db.flush()
        return category

    def get_in_workspace(self, *, workspace_id: str, category_id: str) -> TicketCategory | None:
        stmt = select(TicketCategory).where(
            TicketCategory.id == category_id, TicketCategory.workspace_id == workspace_id
        )
        return self.db.scalar(stmt)

    def list_in_workspace(self, *, workspace_id: str) -> list[TicketCategory]:
        stmt = (
            select(TicketCategory)
            .where(TicketCategory.workspace_id == workspace_id)
            .order_by(TicketCategory.name)
        )
        return list(self.db.scalars(stmt))


class TagRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, workspace_id: str, name: str, color: str = "") -> Tag:
        tag = Tag(workspace_id=workspace_id, name=name, color=color)
        self.db.add(tag)
        self.db.flush()
        return tag

    def get_in_workspace(self, *, workspace_id: str, tag_id: str) -> Tag | None:
        stmt = select(Tag).where(Tag.id == tag_id, Tag.workspace_id == workspace_id)
        return self.db.scalar(stmt)

    def list_in_workspace(self, *, workspace_id: str) -> list[Tag]:
        stmt = select(Tag).where(Tag.workspace_id == workspace_id).order_by(Tag.name)
        return list(self.db.scalars(stmt))
