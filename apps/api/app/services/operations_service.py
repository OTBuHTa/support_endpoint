from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.base import utcnow
from app.models.operations import Notification, NotificationType, SLAPolicy, SupportTask, TaskStatus
from app.models.ticket import Ticket
from app.models.ticket_enums import TicketPriority
from app.repositories.audit_repo import AuditRepository
from app.repositories.operations_repo import OperationsRepository
from app.repositories.ticket_repo import TicketRepository
from app.repositories.workspace_repo import MembershipRepository

_DEFAULT_SLA: dict[TicketPriority, tuple[int, int, int]] = {
    TicketPriority.LOW: (240, 2880, 60),
    TicketPriority.MEDIUM: (120, 1440, 30),
    TicketPriority.HIGH: (60, 480, 15),
    TicketPriority.URGENT: (15, 240, 5),
}


class OperationsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = OperationsRepository(db)
        self.tickets = TicketRepository(db)
        self.memberships = MembershipRepository(db)
        self.audit = AuditRepository(db)

    def _ticket(self, *, workspace_id: str, ticket_id: str) -> Ticket:
        ticket = self.tickets.get_in_workspace(workspace_id=workspace_id, ticket_id=ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found")
        return ticket

    def _validate_member(self, *, workspace_id: str, user_id: str | None) -> None:
        if user_id is None:
            return
        if self.memberships.get(workspace_id=workspace_id, user_id=user_id) is None:
            raise ValidationAppError("assignee_user_id is not a member of this workspace")

    def ensure_policy(self, *, workspace_id: str, priority: TicketPriority) -> SLAPolicy:
        policy = self.repo.get_policy(workspace_id=workspace_id, priority=priority)
        if policy is not None:
            return policy
        first_response, resolution, warning = _DEFAULT_SLA[priority]
        return self.repo.upsert_policy(
            workspace_id=workspace_id,
            priority=priority,
            first_response_minutes=first_response,
            resolution_minutes=resolution,
            warning_minutes_before=warning,
        )

    def attach_sla(self, *, ticket: Ticket) -> None:
        if self.repo.get_ticket_sla(workspace_id=ticket.workspace_id, ticket_id=ticket.id) is not None:
            return
        policy = self.ensure_policy(workspace_id=ticket.workspace_id, priority=ticket.priority)
        base = ticket.created_at or utcnow()
        self.repo.create_ticket_sla(
            workspace_id=ticket.workspace_id,
            ticket_id=ticket.id,
            policy_id=policy.id,
            first_response_due_at=base + timedelta(minutes=policy.first_response_minutes),
            resolution_due_at=base + timedelta(minutes=policy.resolution_minutes),
        )

    def mark_first_response(self, *, workspace_id: str, ticket_id: str) -> None:
        item = self.repo.get_ticket_sla(workspace_id=workspace_id, ticket_id=ticket_id)
        if item is None or item.first_response_at is not None:
            return
        item.first_response_at = utcnow()
        item.first_response_breached = item.first_response_at > item.first_response_due_at
        self.db.add(item)

    def mark_resolved(self, *, workspace_id: str, ticket_id: str) -> None:
        item = self.repo.get_ticket_sla(workspace_id=workspace_id, ticket_id=ticket_id)
        if item is None or item.resolved_at is not None:
            return
        item.resolved_at = utcnow()
        item.resolution_breached = item.resolved_at > item.resolution_due_at
        self.db.add(item)

    def create_task(
        self,
        *,
        workspace_id: str,
        ticket_id: str,
        actor_user_id: str,
        title: str,
        description: str,
        assignee_user_id: str | None,
        due_at,
    ) -> SupportTask:
        ticket = self._ticket(workspace_id=workspace_id, ticket_id=ticket_id)
        self._validate_member(workspace_id=workspace_id, user_id=assignee_user_id)
        task = self.repo.create_task(
            workspace_id=workspace_id,
            ticket_id=ticket_id,
            creator_user_id=actor_user_id,
            assignee_user_id=assignee_user_id,
            title=title,
            description=description,
            due_at=due_at,
        )
        if assignee_user_id is not None:
            self.repo.create_notification(
                workspace_id=workspace_id,
                user_id=assignee_user_id,
                ticket_id=ticket.id,
                type=NotificationType.TASK_ASSIGNED,
                title=f"Task assigned: {title}",
                body=f"Ticket: {ticket.subject}",
            )
        self.audit.record(
            action="operations.task.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="support_task",
            resource_id=task.id,
            metadata={"ticket_id": ticket_id, "assignee_user_id": assignee_user_id},
        )
        self.db.commit()
        return task

    def list_tasks(self, *, workspace_id: str, ticket_id: str | None = None) -> list[SupportTask]:
        if ticket_id is not None:
            self._ticket(workspace_id=workspace_id, ticket_id=ticket_id)
        return self.repo.list_tasks(workspace_id=workspace_id, ticket_id=ticket_id)

    def set_task_status(
        self,
        *,
        workspace_id: str,
        task_id: str,
        actor_user_id: str,
        status: TaskStatus,
    ) -> SupportTask:
        task = self.repo.get_task(workspace_id=workspace_id, task_id=task_id)
        if task is None:
            raise NotFoundError("Task not found")
        if task.status != TaskStatus.OPEN:
            raise ValidationAppError("Only open tasks can change status")
        if status not in {TaskStatus.DONE, TaskStatus.CANCELLED}:
            raise ValidationAppError("Task can only be completed or cancelled")
        task.status = status
        if status == TaskStatus.DONE:
            task.completed_at = utcnow()
        self.db.add(task)
        self.audit.record(
            action="operations.task.status_changed",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="support_task",
            resource_id=task.id,
            metadata={"status": status.value},
        )
        self.db.commit()
        return task

    def upsert_policy(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        priority: TicketPriority,
        first_response_minutes: int,
        resolution_minutes: int,
        warning_minutes_before: int,
    ) -> SLAPolicy:
        if warning_minutes_before >= min(first_response_minutes, resolution_minutes):
            raise ValidationAppError("warning window must be smaller than both SLA targets")
        policy = self.repo.upsert_policy(
            workspace_id=workspace_id,
            priority=priority,
            first_response_minutes=first_response_minutes,
            resolution_minutes=resolution_minutes,
            warning_minutes_before=warning_minutes_before,
        )
        self.audit.record(
            action="operations.sla_policy.updated",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="sla_policy",
            resource_id=policy.id,
            metadata={"priority": priority.value},
        )
        self.db.commit()
        return policy

    def list_policies(self, *, workspace_id: str) -> list[SLAPolicy]:
        return self.repo.list_policies(workspace_id=workspace_id)

    def get_ticket_sla(self, *, workspace_id: str, ticket_id: str):
        self._ticket(workspace_id=workspace_id, ticket_id=ticket_id)
        item = self.repo.get_ticket_sla(workspace_id=workspace_id, ticket_id=ticket_id)
        if item is None:
            raise NotFoundError("Ticket SLA not found")
        return item

    def notify_ticket_assignment(self, *, ticket: Ticket, user_id: str | None) -> None:
        if user_id is None:
            return
        self.repo.create_notification(
            workspace_id=ticket.workspace_id,
            user_id=user_id,
            ticket_id=ticket.id,
            type=NotificationType.TICKET_ASSIGNED,
            title=f"Ticket assigned: {ticket.subject}",
        )

    def evaluate_sla(self, *, workspace_id: str) -> tuple[int, int, int]:
        now = utcnow()
        evaluated = warnings = breaches = 0
        for item in self.repo.list_active_slas(workspace_id=workspace_id):
            evaluated += 1
            policy = self.db.get(SLAPolicy, item.policy_id)
            ticket = self.tickets.get_in_workspace(workspace_id=workspace_id, ticket_id=item.ticket_id)
            if policy is None or ticket is None:
                continue
            user_id = ticket.assignee_user_id or ticket.creator_user_id
            warning_delta = timedelta(minutes=policy.warning_minutes_before)

            if item.first_response_at is None:
                if now >= item.first_response_due_at and not item.first_response_breached:
                    item.first_response_breached = True
                    breaches += 1
                    self._sla_notification(ticket, user_id, "First response SLA breached", True)
                elif (
                    now >= item.first_response_due_at - warning_delta
                    and not item.first_response_warning_sent
                ):
                    item.first_response_warning_sent = True
                    warnings += 1
                    self._sla_notification(ticket, user_id, "First response SLA approaching", False)

            if item.resolved_at is None:
                if now >= item.resolution_due_at and not item.resolution_breached:
                    item.resolution_breached = True
                    breaches += 1
                    self._sla_notification(ticket, user_id, "Resolution SLA breached", True)
                elif now >= item.resolution_due_at - warning_delta and not item.resolution_warning_sent:
                    item.resolution_warning_sent = True
                    warnings += 1
                    self._sla_notification(ticket, user_id, "Resolution SLA approaching", False)
            self.db.add(item)
        self.db.commit()
        return evaluated, warnings, breaches

    def _sla_notification(self, ticket: Ticket, user_id: str, title: str, breached: bool) -> None:
        self.repo.create_notification(
            workspace_id=ticket.workspace_id,
            user_id=user_id,
            ticket_id=ticket.id,
            type=NotificationType.SLA_BREACHED if breached else NotificationType.SLA_WARNING,
            title=title,
            body=ticket.subject,
        )

    def list_notifications(self, *, workspace_id: str, user_id: str) -> list[Notification]:
        return self.repo.list_notifications(workspace_id=workspace_id, user_id=user_id)

    def mark_notification_read(
        self, *, workspace_id: str, user_id: str, notification_id: str
    ) -> Notification:
        item = self.repo.get_notification(
            workspace_id=workspace_id, user_id=user_id, notification_id=notification_id
        )
        if item is None:
            raise NotFoundError("Notification not found")
        if item.read_at is None:
            item.read_at = utcnow()
            self.db.add(item)
            self.db.commit()
        return item
