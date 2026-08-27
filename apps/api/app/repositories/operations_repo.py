from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.communication import Conversation, Message, MessageDirection
from app.models.operations import Notification, NotificationType, SLAPolicy, SupportTask, TicketSLA
from app.models.ticket_enums import TicketPriority


class OperationsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_task(self, **values) -> SupportTask:
        item = SupportTask(**values)
        self.db.add(item)
        self.db.flush()
        return item

    def get_task(self, *, workspace_id: str, task_id: str) -> SupportTask | None:
        return self.db.scalar(
            select(SupportTask).where(
                SupportTask.id == task_id,
                SupportTask.workspace_id == workspace_id,
            )
        )

    def list_tasks(
        self, *, workspace_id: str, ticket_id: str | None = None
    ) -> list[SupportTask]:
        stmt = select(SupportTask).where(SupportTask.workspace_id == workspace_id)
        if ticket_id:
            stmt = stmt.where(SupportTask.ticket_id == ticket_id)
        return list(self.db.scalars(stmt.order_by(SupportTask.created_at.desc())))

    def get_policy(self, *, workspace_id: str, priority: TicketPriority) -> SLAPolicy | None:
        return self.db.scalar(
            select(SLAPolicy).where(
                SLAPolicy.workspace_id == workspace_id,
                SLAPolicy.priority == priority,
                SLAPolicy.is_active.is_(True),
            )
        )

    def upsert_policy(
        self,
        *,
        workspace_id: str,
        priority: TicketPriority,
        first_response_minutes: int,
        resolution_minutes: int,
        warning_minutes_before: int,
    ) -> SLAPolicy:
        item = self.db.scalar(
            select(SLAPolicy).where(
                SLAPolicy.workspace_id == workspace_id,
                SLAPolicy.priority == priority,
            )
        )
        if item is None:
            item = SLAPolicy(workspace_id=workspace_id, priority=priority)
        item.first_response_minutes = first_response_minutes
        item.resolution_minutes = resolution_minutes
        item.warning_minutes_before = warning_minutes_before
        item.is_active = True
        self.db.add(item)
        self.db.flush()
        return item

    def list_policies(self, *, workspace_id: str) -> list[SLAPolicy]:
        stmt = (
            select(SLAPolicy)
            .where(SLAPolicy.workspace_id == workspace_id)
            .order_by(SLAPolicy.priority)
        )
        return list(self.db.scalars(stmt))

    def create_ticket_sla(self, **values) -> TicketSLA:
        item = TicketSLA(**values)
        self.db.add(item)
        self.db.flush()
        return item

    def get_ticket_sla(self, *, workspace_id: str, ticket_id: str) -> TicketSLA | None:
        return self.db.scalar(
            select(TicketSLA).where(
                TicketSLA.workspace_id == workspace_id,
                TicketSLA.ticket_id == ticket_id,
            )
        )

    def list_active_slas(self, *, workspace_id: str) -> list[TicketSLA]:
        stmt = select(TicketSLA).where(
            TicketSLA.workspace_id == workspace_id,
            (TicketSLA.first_response_at.is_(None)) | (TicketSLA.resolved_at.is_(None)),
        )
        return list(self.db.scalars(stmt))

    def first_outbound_at(self, *, workspace_id: str, ticket_id: str):
        stmt = (
            select(Message.created_at)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Conversation.workspace_id == workspace_id,
                Conversation.ticket_id == ticket_id,
                Message.workspace_id == workspace_id,
                Message.direction == MessageDirection.OUTBOUND,
            )
            .order_by(Message.created_at.asc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def ticket_status_events(self, *, workspace_id: str, ticket_id: str) -> list[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.workspace_id == workspace_id,
                AuditEvent.resource_type == "ticket",
                AuditEvent.resource_id == ticket_id,
                AuditEvent.action == "servicedesk.ticket.status_changed",
            )
            .order_by(AuditEvent.created_at.asc())
        )
        return list(self.db.scalars(stmt))

    def create_notification(
        self,
        *,
        workspace_id: str,
        user_id: str,
        type: NotificationType,
        title: str,
        body: str = "",
        ticket_id: str | None = None,
    ) -> Notification:
        item = Notification(
            workspace_id=workspace_id,
            user_id=user_id,
            ticket_id=ticket_id,
            type=type,
            title=title,
            body=body,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def list_notifications(self, *, workspace_id: str, user_id: str) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(
                Notification.workspace_id == workspace_id,
                Notification.user_id == user_id,
            )
            .order_by(Notification.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def get_notification(
        self, *, workspace_id: str, user_id: str, notification_id: str
    ) -> Notification | None:
        return self.db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.workspace_id == workspace_id,
                Notification.user_id == user_id,
            )
        )
