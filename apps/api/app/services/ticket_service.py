from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.client import Client
from app.models.ticket import Ticket
from app.models.ticket_enums import TicketPriority, TicketStatus, is_transition_allowed
from app.repositories.audit_repo import AuditRepository
from app.repositories.client_repo import ClientRepository
from app.repositories.ticket_lookup_repo import (
    QueueRepository,
    TagRepository,
    TicketCategoryRepository,
)
from app.repositories.ticket_repo import (
    TicketAssignmentRepository,
    TicketRepository,
    TicketTagRepository,
)
from app.repositories.workspace_repo import MembershipRepository


class TicketService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.tickets = TicketRepository(db)
        self.clients = ClientRepository(db)
        self.queues = QueueRepository(db)
        self.categories = TicketCategoryRepository(db)
        self.tags = TagRepository(db)
        self.ticket_tags = TicketTagRepository(db)
        self.assignments = TicketAssignmentRepository(db)
        self.memberships = MembershipRepository(db)
        self.audit = AuditRepository(db)

    # --- validation helpers -------------------------------------------------

    def _validate_client(self, *, workspace_id: str, client_id: str) -> Client:
        client = self.clients.get_in_workspace(workspace_id=workspace_id, client_id=client_id)
        if client is None:
            raise ValidationAppError("client_id does not refer to a client in this workspace")
        return client

    def _validate_queue(self, *, workspace_id: str, queue_id: str | None) -> None:
        if queue_id is None:
            return
        if self.queues.get_in_workspace(workspace_id=workspace_id, queue_id=queue_id) is None:
            raise ValidationAppError("queue_id does not refer to a queue in this workspace")

    def _validate_category(self, *, workspace_id: str, category_id: str | None) -> None:
        if category_id is None:
            return
        if (
            self.categories.get_in_workspace(workspace_id=workspace_id, category_id=category_id)
            is None
        ):
            raise ValidationAppError("category_id does not refer to a category in this workspace")

    def _validate_assignee(self, *, workspace_id: str, assignee_user_id: str | None) -> None:
        if assignee_user_id is None:
            return
        membership = self.memberships.get(workspace_id=workspace_id, user_id=assignee_user_id)
        if membership is None:
            raise ValidationAppError("assignee_user_id is not a member of this workspace")

    # --- core operations ------------------------------------------------

    def create(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        client_id: str,
        subject: str,
        description: str = "",
        priority: TicketPriority = TicketPriority.MEDIUM,
        queue_id: str | None = None,
        category_id: str | None = None,
    ) -> Ticket:
        self._validate_client(workspace_id=workspace_id, client_id=client_id)
        self._validate_queue(workspace_id=workspace_id, queue_id=queue_id)
        self._validate_category(workspace_id=workspace_id, category_id=category_id)

        ticket = self.tickets.create(
            workspace_id=workspace_id,
            client_id=client_id,
            creator_user_id=actor_user_id,
            subject=subject,
            description=description,
            priority=priority,
            queue_id=queue_id,
            category_id=category_id,
        )
        self.audit.record(
            action="servicedesk.ticket.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="ticket",
            resource_id=ticket.id,
            metadata={"status": ticket.status.value, "priority": ticket.priority.value},
        )
        self.db.commit()
        return self.get(workspace_id=workspace_id, ticket_id=ticket.id)

    def get(self, *, workspace_id: str, ticket_id: str) -> Ticket:
        ticket = self.tickets.get_in_workspace(workspace_id=workspace_id, ticket_id=ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found")
        return ticket

    def list(
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
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        return self.tickets.list_in_workspace(
            workspace_id=workspace_id,
            q=q,
            status=status,
            priority=priority,
            queue_id=queue_id,
            category_id=category_id,
            assignee_user_id=assignee_user_id,
            client_id=client_id,
            limit=limit,
            offset=offset,
        )

    def update(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        ticket_id: str,
        subject: str | None = None,
        description: str | None = None,
        priority: TicketPriority | None = None,
        queue_id: str | None = None,
        category_id: str | None = None,
    ) -> Ticket:
        ticket = self.get(workspace_id=workspace_id, ticket_id=ticket_id)
        if queue_id is not None:
            self._validate_queue(workspace_id=workspace_id, queue_id=queue_id)
            ticket.queue_id = queue_id
        if category_id is not None:
            self._validate_category(workspace_id=workspace_id, category_id=category_id)
            ticket.category_id = category_id
        if subject is not None:
            ticket.subject = subject
        if description is not None:
            ticket.description = description
        if priority is not None:
            ticket.priority = priority
        self.db.add(ticket)
        self.audit.record(
            action="servicedesk.ticket.updated",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="ticket",
            resource_id=ticket.id,
        )
        self.db.commit()
        return self.get(workspace_id=workspace_id, ticket_id=ticket.id)

    def transition_status(
        self, *, workspace_id: str, actor_user_id: str, ticket_id: str, target_status: TicketStatus
    ) -> Ticket:
        """Server-controlled state machine — see
        `app.models.ticket_enums.ALLOWED_TRANSITIONS`. Callers (the
        router) are responsible for the additional `tickets.close`
        permission check when `target_status == CLOSED`; this method
        enforces the state machine itself regardless of caller.
        """
        ticket = self.get(workspace_id=workspace_id, ticket_id=ticket_id)
        if not is_transition_allowed(ticket.status, target_status):
            raise ValidationAppError(
                f"Cannot transition ticket from '{ticket.status.value}' to '{target_status.value}'"
            )
        previous_status = ticket.status
        ticket.status = target_status
        self.db.add(ticket)
        self.audit.record(
            action="servicedesk.ticket.status_changed",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="ticket",
            resource_id=ticket.id,
            metadata={"from": previous_status.value, "to": target_status.value},
        )
        self.db.commit()
        return self.get(workspace_id=workspace_id, ticket_id=ticket.id)

    def assign(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        ticket_id: str,
        assignee_user_id: str | None,
    ) -> Ticket:
        ticket = self.get(workspace_id=workspace_id, ticket_id=ticket_id)
        self._validate_assignee(workspace_id=workspace_id, assignee_user_id=assignee_user_id)

        ticket.assignee_user_id = assignee_user_id
        self.db.add(ticket)
        self.assignments.create(
            workspace_id=workspace_id,
            ticket_id=ticket_id,
            assignee_user_id=assignee_user_id,
            assigned_by_user_id=actor_user_id,
        )
        self.audit.record(
            action="servicedesk.ticket.assigned",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="ticket",
            resource_id=ticket.id,
            metadata={"assignee_user_id": assignee_user_id},
        )
        self.db.commit()
        return self.get(workspace_id=workspace_id, ticket_id=ticket.id)

    def assignment_history(self, *, workspace_id: str, ticket_id: str):
        self.get(workspace_id=workspace_id, ticket_id=ticket_id)  # 404s if not in this workspace
        return self.assignments.list_for_ticket(workspace_id=workspace_id, ticket_id=ticket_id)

    def add_tag(
        self, *, workspace_id: str, actor_user_id: str, ticket_id: str, tag_id: str
    ) -> Ticket:
        self.get(workspace_id=workspace_id, ticket_id=ticket_id)
        if self.tags.get_in_workspace(workspace_id=workspace_id, tag_id=tag_id) is None:
            raise ValidationAppError("tag_id does not refer to a tag in this workspace")
        self.ticket_tags.add(ticket_id=ticket_id, tag_id=tag_id)
        self.audit.record(
            action="servicedesk.ticket.tag_added",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="ticket",
            resource_id=ticket_id,
            metadata={"tag_id": tag_id},
        )
        self.db.commit()
        return self.get(workspace_id=workspace_id, ticket_id=ticket_id)

    def remove_tag(
        self, *, workspace_id: str, actor_user_id: str, ticket_id: str, tag_id: str
    ) -> Ticket:
        self.get(workspace_id=workspace_id, ticket_id=ticket_id)
        self.ticket_tags.remove(ticket_id=ticket_id, tag_id=tag_id)
        self.audit.record(
            action="servicedesk.ticket.tag_removed",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="ticket",
            resource_id=ticket_id,
            metadata={"tag_id": tag_id},
        )
        self.db.commit()
        return self.get(workspace_id=workspace_id, ticket_id=ticket_id)
