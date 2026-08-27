from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.ticket import Ticket, TicketAssignment, TicketTag
from app.models.ticket_enums import TicketPriority, TicketStatus


class TicketRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        workspace_id: str,
        client_id: str,
        creator_user_id: str,
        subject: str,
        description: str = "",
        priority: TicketPriority = TicketPriority.MEDIUM,
        queue_id: str | None = None,
        category_id: str | None = None,
    ) -> Ticket:
        ticket = Ticket(
            workspace_id=workspace_id,
            client_id=client_id,
            creator_user_id=creator_user_id,
            subject=subject,
            description=description,
            priority=priority,
            queue_id=queue_id,
            category_id=category_id,
            status=TicketStatus.NEW,
        )
        self.db.add(ticket)
        self.db.flush()
        return ticket

    def get_in_workspace(self, *, workspace_id: str, ticket_id: str) -> Ticket | None:
        """Object-level IDOR guard, same pattern as ClientRepository:
        filters by (id, workspace_id) together so a ticket id from
        another workspace never resolves here.
        """
        stmt = (
            select(Ticket)
            .options(selectinload(Ticket.tags))
            .where(Ticket.id == ticket_id, Ticket.workspace_id == workspace_id)
        )
        return self.db.scalar(stmt)

    def list_in_workspace(
        self,
        *,
        workspace_id: str,
        q: str = "",
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        queue_id: str | None = None,
        category_id: str | None = None,
        assignee_user_id: str | None = None,
        client_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Ticket], int]:
        base = select(Ticket).where(Ticket.workspace_id == workspace_id)
        if status is not None:
            base = base.where(Ticket.status == status)
        if priority is not None:
            base = base.where(Ticket.priority == priority)
        if queue_id is not None:
            base = base.where(Ticket.queue_id == queue_id)
        if category_id is not None:
            base = base.where(Ticket.category_id == category_id)
        if assignee_user_id is not None:
            base = base.where(Ticket.assignee_user_id == assignee_user_id)
        if client_id is not None:
            base = base.where(Ticket.client_id == client_id)
        if q:
            like = f"%{q.lower()}%"
            base = base.where(
                or_(
                    func.lower(Ticket.subject).like(like),
                    func.lower(Ticket.description).like(like),
                )
            )
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = list(
            self.db.scalars(
                base.options(selectinload(Ticket.tags))
                .order_by(Ticket.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        return items, total


class TicketAssignmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        workspace_id: str,
        ticket_id: str,
        assignee_user_id: str | None,
        assigned_by_user_id: str,
    ) -> TicketAssignment:
        record = TicketAssignment(
            workspace_id=workspace_id,
            ticket_id=ticket_id,
            assignee_user_id=assignee_user_id,
            assigned_by_user_id=assigned_by_user_id,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def list_for_ticket(self, *, workspace_id: str, ticket_id: str) -> list[TicketAssignment]:
        stmt = (
            select(TicketAssignment)
            .where(
                TicketAssignment.workspace_id == workspace_id,
                TicketAssignment.ticket_id == ticket_id,
            )
            .order_by(TicketAssignment.created_at)
        )
        return list(self.db.scalars(stmt))


class TicketTagRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, *, ticket_id: str, tag_id: str) -> TicketTag | None:
        stmt = select(TicketTag).where(TicketTag.ticket_id == ticket_id, TicketTag.tag_id == tag_id)
        return self.db.scalar(stmt)

    def add(self, *, ticket_id: str, tag_id: str) -> TicketTag:
        existing = self.get(ticket_id=ticket_id, tag_id=tag_id)
        if existing is not None:
            return existing
        link = TicketTag(ticket_id=ticket_id, tag_id=tag_id)
        self.db.add(link)
        self.db.flush()
        return link

    def remove(self, *, ticket_id: str, tag_id: str) -> None:
        link = self.get(ticket_id=ticket_id, tag_id=tag_id)
        if link is not None:
            self.db.delete(link)
            self.db.flush()
