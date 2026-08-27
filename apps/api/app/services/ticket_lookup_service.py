from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.ticket import Queue, Tag, TicketCategory
from app.repositories.audit_repo import AuditRepository
from app.repositories.ticket_lookup_repo import (
    QueueRepository,
    TagRepository,
    TicketCategoryRepository,
)


class QueueService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.queues = QueueRepository(db)
        self.audit = AuditRepository(db)

    def create(
        self, *, workspace_id: str, actor_user_id: str, name: str, description: str = ""
    ) -> Queue:
        queue = self.queues.create(workspace_id=workspace_id, name=name, description=description)
        self.audit.record(
            action="servicedesk.queue.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="queue",
            resource_id=queue.id,
        )
        self.db.commit()
        return queue

    def get(self, *, workspace_id: str, queue_id: str) -> Queue:
        queue = self.queues.get_in_workspace(workspace_id=workspace_id, queue_id=queue_id)
        if queue is None:
            raise NotFoundError("Queue not found")
        return queue

    def list_all(self, *, workspace_id: str) -> list[Queue]:
        return self.queues.list_in_workspace(workspace_id=workspace_id)

    def update(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        queue_id: str,
        name: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> Queue:
        queue = self.get(workspace_id=workspace_id, queue_id=queue_id)
        if name is not None:
            queue.name = name
        if description is not None:
            queue.description = description
        if is_active is not None:
            queue.is_active = is_active
        self.db.add(queue)
        self.audit.record(
            action="servicedesk.queue.updated",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="queue",
            resource_id=queue.id,
        )
        self.db.commit()
        return queue


class TicketCategoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.categories = TicketCategoryRepository(db)
        self.audit = AuditRepository(db)

    def create(
        self, *, workspace_id: str, actor_user_id: str, name: str, description: str = ""
    ) -> TicketCategory:
        category = self.categories.create(
            workspace_id=workspace_id, name=name, description=description
        )
        self.audit.record(
            action="servicedesk.category.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="ticket_category",
            resource_id=category.id,
        )
        self.db.commit()
        return category

    def get(self, *, workspace_id: str, category_id: str) -> TicketCategory:
        category = self.categories.get_in_workspace(
            workspace_id=workspace_id, category_id=category_id
        )
        if category is None:
            raise NotFoundError("Category not found")
        return category

    def list_all(self, *, workspace_id: str) -> list[TicketCategory]:
        return self.categories.list_in_workspace(workspace_id=workspace_id)

    def update(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        category_id: str,
        name: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> TicketCategory:
        category = self.get(workspace_id=workspace_id, category_id=category_id)
        if name is not None:
            category.name = name
        if description is not None:
            category.description = description
        if is_active is not None:
            category.is_active = is_active
        self.db.add(category)
        self.audit.record(
            action="servicedesk.category.updated",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="ticket_category",
            resource_id=category.id,
        )
        self.db.commit()
        return category


class TagService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.tags = TagRepository(db)
        self.audit = AuditRepository(db)

    def create(self, *, workspace_id: str, actor_user_id: str, name: str, color: str = "") -> Tag:
        tag = self.tags.create(workspace_id=workspace_id, name=name, color=color)
        self.audit.record(
            action="servicedesk.tag.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="tag",
            resource_id=tag.id,
        )
        self.db.commit()
        return tag

    def get(self, *, workspace_id: str, tag_id: str) -> Tag:
        tag = self.tags.get_in_workspace(workspace_id=workspace_id, tag_id=tag_id)
        if tag is None:
            raise NotFoundError("Tag not found")
        return tag

    def list_all(self, *, workspace_id: str) -> list[Tag]:
        return self.tags.list_in_workspace(workspace_id=workspace_id)
